import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait

# ============ ENV ============
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ============ CONFIG ============
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2160p": 4}

# ============ CLIENT ============
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []

# ============ HELPERS ============
def is_owner(uid):
    return uid in OWNERS


def make_bar(p):
    f = int(p // 10)
    return "█" * f + "░" * (10 - f)


def parse_tme_link(link):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)


def parse_episode_message(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("🎺"):
        return None

    t = re.search(r"Episode\s+(\d+)", lines[0])
    overall = t.group(1)

    files = []
    for line in lines[1:]:
        m = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", line)
        if not m:
            continue

        name = m.group(2)
        if "2160" in name:
            q = "2160p"
        elif "1080" in name:
            q = "1080p"
        elif "720" in name:
            q = "720p"
        else:
            q = "480p"

        files.append({
            "link": m.group(1),
            "filename": name,
            "quality": q
        })

    return {
        "title": lines[0],
        "overall": overall,
        "files": sorted(files, key=lambda x: QUALITY_ORDER[x["quality"]])
    }


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

# ============ THUMB ============
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Photo ke reply me /set_thumb bhejo")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail set successfully")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ============ QUEUE ============
@app.on_message(filters.text & filters.regex(r"^🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    data = parse_episode_message(m.text)
    if data:
        EPISODE_QUEUE.append(data)
        await m.reply(f"📥 Queued → {data['title']}")

# ============ START ============
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    status = await m.reply("🚀 Starting...")
    last_edit = 0

    async def progress(cur, total, stage, start):
        nonlocal last_edit
        now = time.time()
        if now - last_edit < 6:
            return
        last_edit = now

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

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"])
        done_lines = []

        for item in ep["files"]:
            chat, mid = parse_tme_link(item["link"])
            src = await client.get_messages(chat, mid)

            start = time.time()
            path = await client.download_media(
                src,
                progress=lambda c, t: progress(c, t, "⬇️ DOWNLOADING", start)
            )

            start = time.time()
            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(item["filename"], item["quality"], ep["overall"]),
                file_name=item["filename"],
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                progress=lambda c, t: progress(c, t, "⬆️ UPLOADING", start)
            )

            os.remove(path)
            done_lines.append(f"{item['filename']} ✅")
            await asyncio.sleep(3)

        await m.reply(
            f"{ep['title']}\n\n" + "\n".join(done_lines)
        )

    EPISODE_QUEUE.clear()
    await status.edit("✅ All episodes completed")

print("🤖 Anime Qualifier — FINAL HUMAN LOGIC BUILD")
app.run()
