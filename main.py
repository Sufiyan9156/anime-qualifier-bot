import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2160p": 4}

app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []

def is_owner(uid):
    return uid in OWNERS

def parse_tme_link(link: str):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)

def parse_episode_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("🎺"):
        return None

    t = re.search(r"Episode\s+(\d+)", lines[0])
    overall = t.group(1) if t else "001"

    files = []
    for line in lines[1:]:
        m = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", line)
        if not m:
            continue

        filename = m.group(2)
        q = "2160p" if "2160" in filename else \
            "1080p" if "1080" in filename else \
            "720p" if "720" in filename else "480p"

        files.append({
            "link": m.group(1),
            "filename": filename,
            "quality": q
        })

    return {
        "title": lines[0],
        "overall": overall,
        "files": sorted(files, key=lambda x: QUALITY_ORDER[x["quality"]])
    }

def build_caption(filename, quality, overall):
    m = re.search(r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)", filename)
    anime, season, ep = m.groups() if m else ("Anime", "01", "01")

    return (
        f"⬡ {anime}\n"
        f"╔══════════════════════╗\n"
        f"‣ Season : {season.zfill(2)}\n"
        f"‣ Episode : {ep.zfill(2)} ({overall})\n"
        f"‣ Audio : Hindi #Official\n"
        f"‣ Quality : {quality}\n"
        f"╚══════════════════════╝\n"
        f"⬡ Uploaded By : {UPLOAD_TAG}"
    )

def make_progress_bar(percent):
    filled = int(percent // 10)
    return "■" * filled + "▢" * (10 - filled)

@app.on_message(filters.text & filters.regex(r"^🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    data = parse_episode_message(m.text)
    if data:
        EPISODE_QUEUE.append(data)
        await m.reply(f"📥 Queued → {data['title']}")

@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    status = await m.reply("🚀 Starting upload...")
    last_update = 0

    async def progress(current, total, stage):
        nonlocal last_update
        now = time.time()
        if now - last_update < 8:
            return
        last_update = now

        percent = current * 100 / total if total else 0
        bar = make_progress_bar(percent)
        speed = (current / max(1, now - start_time)) / (1024 * 1024)

        try:
            await status.edit(
                f"**{stage}**\n"
                f"`{bar}` {percent:.1f}%\n"
                f"⚡ {speed:.2f} MB/s"
            )
        except (MessageNotModified, FloodWait):
            pass

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"])

        for item in ep["files"]:
            try:
                chat, msg_id = parse_tme_link(item["link"])
                src = await client.get_messages(chat, msg_id)

                start_time = time.time()
                await status.edit("⬇️ Downloading...")
                path = await client.download_media(
                    src,
                    progress=lambda c, t: progress(c, t, "⬇️ Downloading")
                )

                start_time = time.time()
                await status.edit("⬆️ Uploading...")
                await client.send_video(
                    m.chat.id,
                    path,
                    caption=build_caption(
                        item["filename"],
                        item["quality"],
                        ep["overall"]
                    ),
                    file_name=item["filename"],
                    thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                    supports_streaming=True,
                    progress=lambda c, t: progress(c, t, "⬆️ Uploading")
                )

                os.remove(path)
                await asyncio.sleep(5)

            except FloodWait as e:
                await asyncio.sleep(e.value + 5)

    EPISODE_QUEUE.clear()
    await status.edit("✅ All uploads completed")

print("🤖 Anime Qualifier — PROGRESS SAFE BUILD")
app.run()
