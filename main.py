import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2160p": 4}

# ================= CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS


def parse_tme_link(link: str):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def parse_episode_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("🎺"):
        return None

    title_line = lines[0]  # 🎺 Episode 025 - Hidden Inventory

    t = re.search(r"Episode\s+(\d+)", title_line)
    overall = t.group(1) if t else "001"

    files = []
    for line in lines[1:]:
        m = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", line)
        if not m:
            continue

        link = m.group(1)
        filename = m.group(2)

        if "2160" in filename or "4k" in filename:
            q = "2160p"
        elif "1080" in filename:
            q = "1080p"
        elif "720" in filename:
            q = "720p"
        else:
            q = "480p"

        files.append({
            "link": link,
            "filename": filename,
            "quality": q
        })

    return {
        "title": title_line,
        "overall": overall,
        "files": sorted(files, key=lambda x: QUALITY_ORDER[x["quality"]])
    }


def build_caption(title_line: str, filename: str, quality: str, overall: str) -> str:
    m = re.search(
        r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)\(",
        filename,
        re.IGNORECASE
    )

    if m:
        anime = m.group(1).strip()
        season = m.group(2).zfill(2)
        episode = m.group(3).zfill(2)
    else:
        anime = "Anime"
        season = "01"
        episode = "01"

    return (
        f"**⬡ {anime}**\n"
        f"**╔══════════════════════╗**\n"
        f"**‣ Season : {season}**\n"
        f"**‣ Episode : {episode} ({overall})**\n"
        f"**‣ Audio : Hindi #Official**\n"
        f"**‣ Quality : {quality}**\n"
        f"**╚══════════════════════╝**\n"
        f"**⬡ Uploaded By: {UPLOAD_TAG}**"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(client: Client, m: Message):
    if not m.from_user or m.from_user.id not in OWNERS:
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ PHOTO ke reply me /set_thumb bhejo")

    try:
        if os.path.exists(THUMB_PATH):
            os.remove(THUMB_PATH)

        await client.download_media(m.reply_to_message.photo, THUMB_PATH)

        if os.path.getsize(THUMB_PATH) > MAX_THUMB_SIZE:
            os.remove(THUMB_PATH)
            return await m.reply("❌ Thumbnail 200KB se bada hai")

        await m.reply("✅ Thumbnail set ho gaya")
    except Exception as e:
        await m.reply("❌ Thumbnail save failed")

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"^🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    data = parse_episode_message(m.text)
    if not data:
        return

    EPISODE_QUEUE.append(data)
    await m.reply(f"📥 Episode queued → {data['title']}")

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message)
    if not is_owner(m.from_user.id):
        return

    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    status = await m.reply("🚀 Uploading...")

    for ep in EPISODE_QUEUE:
        await m.reply(f"**{ep['title']}**")

        for item in ep["files"]:
            chat, msg_id = parse_tme_link(item["link"])
            if not chat:
                continue

            source = await client.get_messages(chat, msg_id)
            start = time.time()

            async def progress(cur, total):
                percent = int(cur * 100 / total)
                speed = (cur / max(1, time.time() - start)) / (1024 * 1024)
                bar = "■" * (percent // 10) + "▢" * (10 - percent // 10)
                try:
                    await status.edit(
                        f"**Status: Processing**\n"
                        f"**{bar} {percent}%**\n"
                        f"**⏩ {speed:.2f} MB/s**"
                    )
                except MessageNotModified:
                    pass

            path = await client.download_media(source, progress=progress)

            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(
                    ep["title"],
                    item["filename"],
                    item["quality"],
                    ep["overall"]
                ),
                file_name=item["filename"],
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                progress=progress
            )

            os.remove(path)
            await asyncio.sleep(1)

    EPISODE_QUEUE.clear()
    await status.edit("✅ All episodes uploaded")

print("🤖 Anime Qualifier — FINAL STABLE GOD BUILD")
app.run()
