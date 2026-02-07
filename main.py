import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"])
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []
PAUSED = False

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def make_bar(p):
    f = int(p // 10)
    return "▰" * f + "▱" * (10 - f)

def speed_fmt(done, start):
    sp = done / max(1, time.time() - start)
    return f"{sp / (1024*1024):.2f} MB/s"

def parse_tme_link(link):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)

# ================= TITLE FORMAT =================
def format_title(raw):
    m = re.match(r"🎺\s*(Episode\s+\d+)\s+–\s+(.+)", raw)
    if not m:
        return f"<b>{raw}</b>"
    ep, name = m.groups()
    return f"<b>🎺 {ep} – <i>{name}</i></b>"

# ================= PARSER =================
def parse_multi_episode(text):
    blocks = re.split(r"(?=🎺)", text)
    episodes = []

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines or not lines[0].startswith("🎺"):
            continue

        raw_title = lines[0]
        title = format_title(raw_title)
        overall = re.search(r"Episode\s+(\d+)", raw_title).group(1)

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
        episodes.append({"title": title, "overall": overall, "files": files})

    return episodes

# ================= CAPTION =================
def build_caption(filename, quality, overall):
    anime, season, ep = re.search(
        r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)", filename
    ).groups()

    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>╔══════════════════════╗</b>\n"
        f"<b>‣ Season : {season.zfill(2)}</b>\n"
        f"<b>‣ Episode : {ep.zfill(2)} ({overall})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Reply photo ke saath /set_thumb bhejo")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail set")

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    for ep in parse_multi_episode(m.text):
        EPISODE_QUEUE.append(ep)
        await m.reply(f"📥 Queued → {ep['title']}", parse_mode=ParseMode.HTML)

# ================= CONTROL =================
@app.on_message(filters.command("stop"))
async def stop(_, m: Message):
    global PAUSED
    PAUSED = True
    await m.reply("⏸ Paused")

@app.on_message(filters.command("resume"))
async def resume(_, m: Message):
    global PAUSED
    PAUSED = False
    await m.reply("▶️ Resumed")

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    final_summary = []

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)
        done = []

        for item in ep["files"]:
            while PAUSED:
                await asyncio.sleep(2)

            chat, mid = parse_tme_link(item["link"])
            src = await client.get_messages(chat, mid)

            prog = await m.reply(
                "📥 DOWNLOADING\n▱▱▱▱▱▱▱▱▱▱ 0%\n⏩ 0.00 MB/s"
            )

            start = time.time()
            last = 0

            async def progress(cur, total, stage):
                nonlocal last
                if time.time() - last < 3:
                    return
                last = time.time()
                p = cur * 100 / total if total else 0
                await prog.edit(
                    f"{stage}\n{make_bar(p)} {int(p)}%\n⏩ {speed_fmt(cur, start)}"
                )

            path = await client.download_media(
                src,
                progress=lambda c, t: progress(c, t, "📥 DOWNLOADING")
            )

            start = time.time()
            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(item["filename"], item["quality"], ep["overall"]),
                file_name=item["filename"],
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                progress=lambda c, t: progress(c, t, "📤 UPLOADING"),
                parse_mode=ParseMode.HTML
            )

            await prog.delete()
            os.remove(path)
            done.append(f"<b>{item['quality']} ✅</b>")

        final_summary.append(ep["title"] + "<br>" + "<br>".join(done))

    EPISODE_QUEUE.clear()

    await m.reply(
        "<br><br>".join(final_summary) + "<br><br><b>✅ All episodes completed</b>",
        parse_mode=ParseMode.HTML
    )

print("🤖 Anime Qualifier — FINAL OPTION B (VIDEO ONLY)")
app.run()
