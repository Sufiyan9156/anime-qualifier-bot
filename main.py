import os
import re
import subprocess
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

THUMB_PATH = "thumb.jpg"

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
def determine_quality(name: str):
    up = name.upper()
    if "2160" in up or "4K" in up:
        return "2k"
    if "1080" in up:
        return "1080p"
    if "720" in up:
        return "720p"
    return "480p"


def parse_filename(name: str):
    up = name.upper()

    anime = "Jujutsu Kaisen"
    season, episode = "01", "01"

    m = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    if m:
        season, episode = m.group(1), m.group(2)

    return {
        "anime": anime,
        "season": f"{int(season):02d}",
        "episode": f"{int(episode):02d}",
        "quality": determine_quality(name)
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
    if m.from_user.id not in OWNERS:
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved (burn mode)")

@app.on_message(filters.command("ping"))
async def ping(_, m):
    await m.reply("✅ Bot alive (ffmpeg mode)")

# =======================
# MAIN HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def process_video(client, message: Message):
    if message.from_user.id not in OWNERS:
        return

    media = message.video or message.document
    if not media:
        return

    status = await message.reply("⬇️ Downloading video...")

    input_video = await message.download()
    info = parse_filename(media.file_name or "video.mp4")

    output_video = build_filename(info)
    caption = build_caption(info)

    await status.edit("🎨 Applying thumbnail (burning)...")

    # FFmpeg command
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", input_video,
        "-i", THUMB_PATH,
        "-filter_complex", "overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "-c:a", "copy",
        output_video
    ], check=True)

    await status.edit("⬆️ Uploading final video...")

    await client.send_video(
        chat_id=message.chat.id,
        video=output_video,
        caption=caption
    )

    await status.edit("✅ Video processed & sent back")

    os.remove(input_video)
    os.remove(output_video)

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot (FFmpeg Burn Mode) LIVE")
app.run()
