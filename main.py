import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "thumb.jpg"

# ================= GLOBALS =================
QUEUE = []   # list of dicts

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS


def extract_info(filename: str):
    name = filename.lower()

    # QUALITY
    if "2160" in name or "4k" in name:
        quality = "2k"
    elif "1080" in name:
        quality = "1080p"
    elif "720" in name:
        quality = "720p"
    else:
        quality = "480p"

    # SEASON / EP
    s, e = 1, 1
    m = re.search(r"s(\d{1,2})\D*e(\d{1,3})", name)
    if m:
        s, e = int(m.group(1)), int(m.group(2))

    season = f"{s:02d}"
    episode = f"{e:02d}"
    overall = f"{e:03d}"

    # CLEAN NAME
    clean = re.sub(
        r"\[.*?\]|s\d+e\d+|\d{3,4}p|4k|hindi|dual|web|hdrip|bluray|x264|x265|aac|mp4|mkv|@\w+",
        "",
        name
    )
    anime = re.sub(r"\s+", " ", clean).strip().title()

    return anime, season, episode, overall, quality


def build_filename(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"


def build_caption(a, s, e, o, q):
    return (
        f"{a}\n\n"
        f"Season : {s}\n"
        f"Episode : {e}({o})\n"
        f"Audio : Hindi #Official\n"
        f"Quality : {q}\n\n"
        f"Uploaded By : {UPLOAD_TAG}"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved (will apply)")

# ================= ADD TO QUEUE =================
@app.on_message(filters.video | filters.document)
async def add_queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    anime, s, e, o, q = extract_info(media.file_name or "video.mp4")

    QUEUE.append({
        "file_id": media.file_id,
        "filename": build_filename(anime, s, e, o, q),
        "caption": build_caption(anime, s, e, o, q)
    })

    await m.reply(f"📥 Added to queue ({len(QUEUE)})")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m: Message):
    if not QUEUE:
        return await m.reply("❌ Nothing to preview")

    last = QUEUE[-1]
    await m.reply(
        f"🧪 PREVIEW (Not Uploaded)\n\n"
        f"Filename:\n{last['filename']}\n\n"
        f"{last['caption']}"
    )

# ================= START UPLOAD =================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    await m.reply(f"🚀 Uploading {len(QUEUE)} videos...")

    while QUEUE:
        item = QUEUE.pop(0)

        path = await client.download_media(item["file_id"])

        await client.send_video(
            chat_id=m.chat.id,
            video=path,
            caption=item["caption"],
            file_name=item["filename"],
            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
            supports_streaming=True
        )

        os.remove(path)
        await asyncio.sleep(1)

    await m.reply("✅ All uploads done")

# ================= RUN =================
print("🤖 Anime Qualifier Bot — FINAL STABLE BUILD")
app.run()
