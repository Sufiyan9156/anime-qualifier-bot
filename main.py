import os
import re
import sqlite3
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
TARGET_CHANNEL_ID = -1002522409883
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_FILE_ID = None

# =======================
# DATABASE
# =======================
db = sqlite3.connect("episodes.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS episodes (key TEXT PRIMARY KEY)")
db.commit()

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


def parse_video_filename(name):
    up = name.upper()

    anime = "JUJUTSU KAISEN" if "JUJUTSU" in up else "UNKNOWN"

    s, e = "01", "01"
    m = re.search(r"S(\d+)E(\d+)", up)
    if m:
        s, e = m.group(1), m.group(2)

    quality = "480p"
    if "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"
    elif "2160" in up or "4K" in up:
        quality = "2k"

    return {
        "anime": anime,
        "season": f"{int(s):02d}",
        "episode": f"{int(e):02d}",
        "quality": quality
    }


def build_caption(i):
    return (
        f"⬡ **{i['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ Season : {i['season']}\n"
        f"┃ Episode : {i['episode']}\n"
        f"┃ Audio : Hindi #Official\n"
        f"┃ Quality : {i['quality']}\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ Uploaded By {UPLOAD_TAG}"
    )


def episode_key(i):
    return f"{i['anime']}_S{i['season']}E{i['episode']}_{i['quality']}"

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("ping"))
async def ping(_, m):
    await m.reply_text("✅ Bot Alive")


@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")
    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply("✅ Thumbnail set")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID)
    else:
        await m.reply("❌ Thumbnail nahi hai")

# =======================
# RE-UPLOAD HANDLER
# =======================
@app.on_message(filters.media)
async def handle_media(client, message: Message):
    print("📥 Media received")

    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media:
        return

    file_name = media.file_name or "video.mp4"
    info = parse_video_filename(file_name)
    key = episode_key(info)

    cur.execute("SELECT key FROM episodes WHERE key=?", (key,))
    if cur.fetchone():
        await message.reply("⛔ Duplicate episode")
        return

    caption = build_caption(info)
    status = await message.reply("📤 Uploading to channel...")

    await client.send_video(
        chat_id=TARGET_CHANNEL_ID,
        video=media.file_id,
        caption=caption,
        thumb=THUMB_FILE_ID
    )

    cur.execute("INSERT OR IGNORE INTO episodes VALUES (?)", (key,))
    db.commit()

    await status.edit("✅ Uploaded successfully")

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE")
app.run()
