import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified

# ================== ENV ==================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================== CONFIG ==================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024

QUALITY_ORDER = {
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "2160p": 4
}

# ================== CLIENT ==================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================== QUEUE ==================
# queue = list of episodes
QUEUE = []

# ================== HELPERS ==================
def is_owner(uid):
    return uid in OWNERS


def parse_block(text: str):
    """
    Returns:
    episode_title: str
    items: list of {link, filename, quality}
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("🎺"):
        return None, []

    episode_title = lines[0]

    items = []
    for line in lines[1:]:
        m = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", line)
        if not m:
            continue

        link = m.group(1)
        filename = m.group(2)

        q = "480p"
        if "2160" in filename:
            q = "2160p"
        elif "1080" in filename:
            q = "1080p"
        elif "720" in filename:
            q = "720p"

        items.append({
            "link": link,
            "filename": filename,
            "quality": q
        })

    items.sort(key=lambda x: QUALITY_ORDER[x["quality"]])
    return episode_title, items


def build_caption(filename: str, quality: str):
    m = re.search(r"Season\s+(\d+)\s+Episode\s+(\d+)\((\d+)\)", filename)
    season = m.group(1) if m else "01"
    ep = m.group(2) if m else "01"
    overall = m.group(3) if m else ep.zfill(3)

    anime = filename.split("Season")[0].strip()

    return (
        f"**⬡ {anime}**\n"
        f"**╔══════════════════════╗**\n"
        f"**‣ Season : {season}**\n"
        f"**‣ Episode : {ep} ({overall})**\n"
        f"**‣ Audio : Hindi #Official**\n"
        f"**‣ Quality : {quality}**\n"
        f"**╚══════════════════════╝**\n"
        f"**⬡ Uploaded By: {UPLOAD_TAG}**"
    )

# ================== THUMB ==================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ **Reply with PHOTO only**")

    try:
        if os.path.exists(THUMB_PATH):
            os.remove(THUMB_PATH)

        await client.download_media(m.reply_to_message.photo, THUMB_PATH)
    except:
        return await m.reply("❌ **Thumbnail download failed**")

    if not os.path.exists(THUMB_PATH):
        return await m.reply("❌ **Thumbnail save failed**")

    if os.path.getsize(THUMB_PATH) > MAX_THUMB_SIZE:
        os.remove(THUMB_PATH)
        return await m.reply("❌ **Thumbnail must be under 200KB**")

    await m.reply("✅ **Custom thumbnail saved**")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("❌ **Thumbnail not set**")


@app.on_message(filters.command("delete_thumb"))
async def delete_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
        await m.reply("🗑 **Thumbnail deleted**")
    else:
        await m.reply("❌ **No thumbnail to delete**")

# ================== ADD BLOCK ==================
@app.on_message(filters.text & filters.private)
async def add_block(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    ep_title, items = parse_block(m.text)
    if not items:
        return

    QUEUE.append({
        "title": ep_title,
        "items": items
    })

    await m.reply(f"📥 **Episode queued → {ep_title}**")

# ================== START ==================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not QUEUE:
        return await m.reply("❌ **Queue empty**")

    for ep in QUEUE:
        await m.reply(f"**{ep['title']}**")

        for item in ep["items"]:
            status = await m.reply("⬇️ Downloading...")
            start = time.time()
            last_edit = 0

            async def progress(cur, total):
                nonlocal last_edit
                now = time.time()
                if now - last_edit < 1:
                    return
                percent = int(cur * 100 / total)
                speed = (cur / max(1, now - start)) / (1024 * 1024)
                bar = "■" * (percent // 10) + "▢" * (10 - percent // 10)
                try:
                    await status.edit(
                        f"**Status**\n"
                        f"**{bar} {percent}%**\n"
                        f"**⏩ {speed:.2f} MB/s**"
                    )
                    last_edit = now
                except MessageNotModified:
                    pass

            msg = await client.get_messages(
                item["link"].split("/")[-2],
                int(item["link"].split("/")[-1])
            )

            path = await client.download_media(msg, progress=progress)

            await client.send_video(
                m.chat.id,
                path,
                file_name=item["filename"],
                caption=build_caption(item["filename"], item["quality"]),
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True
            )

            await status.delete()
            os.remove(path)

    QUEUE.clear()
    await m.reply("✅ **All episodes uploaded successfully**")

# ================== RUN ==================
print("🤖 Anime Qualifier — FINAL DIRECT LINK BUILD LIVE")
app.run()
