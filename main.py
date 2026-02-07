import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait

# ========= ENV =========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ========= CONFIG =========
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ========= CLIENT =========
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []
PAUSED = False

# ========= HELPERS =========
def is_owner(uid):
    return uid in OWNERS

def make_bar(p):
    f = int(p // 10)
    return "█" * f + "░" * (10 - f)

def parse_tme_link(link):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)

# 🔥 MULTI-EPISODE PARSER
def parse_multi_episode(text: str):
    blocks = re.split(r"(?=🎺)", text)
    episodes = []

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines or not lines[0].startswith("🎺"):
            continue

        title = lines[0]
        t = re.search(r"Episode\s+(\d+)", title)
        overall = t.group(1)

        files = []
        for l in lines[1:]:
            m = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", l)
            if not m:
                continue

            name = m.group(2)
            q = next((x for x in QUALITY_ORDER if x in name), "480p")

            files.append({
                "link": m.group(1),
                "filename": name,
                "quality": q
            })

        files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

        episodes.append({
            "title": title,
            "overall": overall,
            "files": files
        })

    return episodes

def build_caption(filename, quality, overall):
    m = re.search(r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)", filename)
    anime, season, ep = m.groups()

    return (
        f"**⬡ {anime}**\n"
        f"**╔══════════════════════╗**\n"
        f"**‣ Season : {season.zfill(2)}**\n"
        f"**‣ Episode : {ep.zfill(2)} ({overall})**\n"
        f"**‣ Audio : Hindi #Official**\n"
        f"**‣ Quality : {quality}**\n"
        f"**╚══════════════════════╝**\n"
        f"**⬡ Uploaded By : {UPLOAD_TAG}**"
    )

# ========= THUMB =========
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Reply photo ke saath /set_thumb bhejo")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail set")

# ========= QUEUE =========
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    eps = parse_multi_episode(m.text)
    for ep in eps:
        EPISODE_QUEUE.append(ep)
        await m.reply(f"📥 Queued → {ep['title']}")

# ========= CONTROL =========
@app.on_message(filters.command("stop"))
async def stop(_, m: Message):
    global PAUSED
    PAUSED = True
    await m.reply("⏸ Upload paused")

@app.on_message(filters.command("resume"))
async def resume(_, m: Message):
    global PAUSED
    PAUSED = False
    await m.reply("▶️ Upload resumed")

# ========= START =========
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"])
        summary = []

        for item in ep["files"]:
            while PAUSED:
                await asyncio.sleep(2)

            chat, mid = parse_tme_link(item["link"])
            src = await client.get_messages(chat, mid)

            status = await m.reply("⬇️ Starting download...")
            start = time.time()
            last = 0

            async def progress(cur, total, stage):
                nonlocal last
                now = time.time()
                if now - last < 5:
                    return
                last = now
                pct = cur * 100 / total if total else 0
                bar = make_bar(pct)
                speed = (cur / max(1, now - start)) / (1024 * 1024)
                try:
                    await status.edit(
                        f"**{stage}**\n"
                        f"**{bar} {pct:.1f}%**\n"
                        f"**⚡ {speed:.2f} MB/s**"
                    )
                except MessageNotModified:
                    pass

            path = await client.download_media(
                src,
                progress=lambda c, t: progress(c, t, "⬇️ DOWNLOADING")
            )

            start = time.time()
            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(item["filename"], item["quality"], ep["overall"]),
                file_name=item["filename"],
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                progress=lambda c, t: progress(c, t, "⬆️ UPLOADING")
            )

            os.remove(path)
            summary.append(f"{item['quality']} ✅")

        await m.reply(f"{ep['title']}\n" + "\n".join(summary))

    EPISODE_QUEUE.clear()
    await m.reply("✅ All episodes completed")

print("🤖 Anime Qualifier — FINAL CORRECT LOGIC BUILD")
app.run()
