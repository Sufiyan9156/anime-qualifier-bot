import os
import re
from pyrogram import Client, filters
from pyrogram.types import Message

# =======================
# ENV
# =======================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# =======================
# CONFIG
# =======================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

BASE_DIR = os.getcwd()
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
THUMB_DIR = os.path.join(BASE_DIR, "thumbs")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

THUMB_PATH = os.path.join(THUMB_DIR, "current.jpg")

# =======================
# BOT
# =======================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# =======================
# HELPERS
# =======================
def is_owner(uid):
    return uid in OWNERS


def parse_video_filename(name: str):
    up = name.upper()

    anime = "JUJUTSU KAISEN" if "JUJUTSU" in up else "UNKNOWN"

    season, episode = "01", "01"
    m = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    if m:
        season, episode = m.group(1), m.group(2)

    quality = "480p"
    if "2160" in up or "4K" in up:
        quality = "2k"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"

    return {
        "anime": anime.title(),
        "season": f"{int(season):02d}",
        "episode": f"{int(episode):02d}",
        "quality": quality
    }


def build_caption(i):
    return (
        f"⬡ **{i['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {i['season']}**\n"
        f"┃ **Episode : {i['episode']}**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {i['quality']}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By {UPLOAD_TAG}**"
    )


def build_filename(i):
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']} "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    await m.reply_to_message.download(file_name=THUMB_PATH)
    await m.reply("✅ Thumbnail set successfully (local)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# =======================
# MAIN HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    if not os.path.exists(THUMB_PATH):
        return await message.reply("❌ Thumbnail set nahi hai")

    media = message.video or message.document
    info = parse_video_filename(media.file_name or "video.mp4")

    caption = build_caption(info)
    filename = build_filename(info)
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    status = await message.reply("⬇️ Downloading video...")
    await message.download(file_name=filepath)

    await status.edit("⬆️ Uploading with custom thumbnail...")

    await client.send_video(
        chat_id=message.chat.id,
        video=filepath,
        caption=caption,
        thumb=THUMB_PATH,
        supports_streaming=True
    )

    await status.edit("✅ Video processed & sent back")

    try:
        os.remove(filepath)
    except:
        pass

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE (Stable Fresh Upload)")
app.run()
