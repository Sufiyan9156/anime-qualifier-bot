import os
import re
import asyncio
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
def is_owner(uid: int) -> bool:
    return uid in OWNERS


def parse_video_filename(name: str):
    up = name.upper()

    anime = "Jujutsu Kaisen" if "JUJUTSU" in up else "Unknown"

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
        "anime": anime,
        "season": f"{int(season):02d}",
        "episode": f"{int(episode):02d}",
        "quality": quality
    }


def build_caption(i: dict) -> str:
    # BOLD + EXACT FORMAT (as you asked)
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


def build_filename(i: dict) -> str:
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']} "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("ping"))
async def ping(_, m: Message):
    await m.reply_text("✅ Anime Qualifier Bot is alive")


@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply_text("❌ Photo ko reply karke /set_thumb bhejo")

    # Download thumbnail locally (IMPORTANT FIX)
    await client.download_media(
        m.reply_to_message.photo,
        file_name=THUMB_PATH
    )

    await m.reply_text("✅ Thumbnail set successfully (local)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply_text("❌ Thumbnail set nahi hai")

# =======================
# MAIN VIDEO HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media:
        return

    info = parse_video_filename(media.file_name or "video.mp4")
    caption = build_caption(info)
    new_name = build_filename(info)

    status = await message.reply_text("⬆️ Uploading… 0%")
    last_percent = -1

    async def progress(current, total):
        nonlocal last_percent
        if total == 0:
            return
        percent = int(current * 100 / total)
        # IMPORTANT: spam & MESSAGE_NOT_MODIFIED fix
        if percent != last_percent and percent % 5 == 0:
            last_percent = percent
            try:
                await status.edit_text(f"⬆️ Uploading… {percent}%")
            except:
                pass

    # Send back to SAME CHAT (bot resend)
    await client.send_video(
        chat_id=message.chat.id,
        video=media.file_id,
        caption=caption,
        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
        file_name=new_name,
        progress=progress
    )

    await status.edit_text("✅ Video processed & sent back")

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE")
app.run()
