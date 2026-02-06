import os
import re
import time
import asyncio
from collections import defaultdict

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

# episode_queue = { title, files[] }
EPISODE_QUEUE = []

# ================= HELPERS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS


def build_caption(filename: str, quality: str) -> str:
    m = re.search(r"(.*?Season\s+\d+)\s+Episode\s+(\d+)\((\d+)\)", filename)
    anime = m.group(1) if m else "Anime"
    ep = m.group(2) if m else "01"
    overall = m.group(3) if m else "001"

    return (
        f"⬡ {anime}\n"
        f"╔══════════════════════╗\n"
        f"‣ Episode : {ep} ({overall})\n"
        f"‣ Audio : Hindi #Official\n"
        f"‣ Quality : {quality}\n"
        f"╚══════════════════════╝\n"
        f"⬡ Uploaded By: {UPLOAD_TAG}"
    )


def parse_episode_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or "🎺" not in lines[0]:
        return None

    title = lines[0]
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
        "title": title,
        "files": sorted(files, key=lambda x: QUALITY_ORDER[x["quality"]])
    }


# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Reply with PHOTO only")

    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)

    await client.download_media(m.reply_to_message.photo, THUMB_PATH)

    if os.path.getsize(THUMB_PATH) > MAX_THUMB_SIZE:
        os.remove(THUMB_PATH)
        return await m.reply("❌ Thumbnail > 200KB")

    await m.reply("✅ Thumbnail saved")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("❌ No thumbnail")


@app.on_message(filters.command("delete_thumb"))
async def delete_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
        await m.reply("✅ Thumbnail deleted")
    else:
        await m.reply("❌ No thumbnail")


# ================= QUEUE =================
@app.on_message(filters.text)
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
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    status = await m.reply("🚀 Starting uploads...")

    for ep in EPISODE_QUEUE:
        await m.reply(f"**{ep['title']}**")

        for item in ep["files"]:
            start = time.time()

            async def progress(cur, total):
                percent = int(cur * 100 / total)
                speed = (cur / max(1, time.time() - start)) / (1024 * 1024)
                bar = "■" * (percent // 10) + "▢" * (10 - percent // 10)

                text = (
                    f"Status: Uploading\n"
                    f"{bar} {percent}%\n"
                    f"⏩ {speed:.2f} MB/s"
                )

                try:
                    await status.edit(text)
                except MessageNotModified:
                    pass

            msg = await client.get_messages(item["link"])
            path = await client.download_media(msg, progress=progress)

            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(item["filename"], item["quality"]),
                file_name=item["filename"],
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True
            )

            os.remove(path)
            await asyncio.sleep(1)

    EPISODE_QUEUE.clear()
    await status.edit("✅ All episodes uploaded")


print("🤖 Anime Qualifier — FINAL STABLE BUILD")
app.run()
