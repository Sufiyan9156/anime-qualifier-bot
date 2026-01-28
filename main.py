import os
import re
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message

# ======================
# ENV (Railway variables)
# ======================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ======================
# CONFIG
# ======================
OWNERS = {2079844068, 6593273878}
TARGET_CHANNEL_ID = -1002522409883  # 🔴 your channel id
UPLOAD_TAG = "@SenpaiAnimess"

BOT_ACTIVE = True
THUMB_FILE_ID = None

# ======================
# DATABASE (duplicate block)
# ======================
db = sqlite3.connect("episodes.db", check_same_thread=False)
cur = db.cursor()
cur.execute(
    "CREATE TABLE IF NOT EXISTS uploaded (key TEXT PRIMARY KEY)"
)
db.commit()

# ======================
# BOT CLIENT
# ======================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ======================
# HELPERS
# ======================
def is_owner(uid: int):
    return uid in OWNERS


def parse_video_filename(name: str):
    up = name.upper()

    anime = "JUJUTSU KAISEN" if "JUJUTSU" in up else "UNKNOWN"

    season = episode = None
    m1 = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    m2 = re.search(r"(\d{1,2})X(\d{1,3})", up)

    if m1:
        season, episode = m1.group(1), m1.group(2)
    elif m2:
        season, episode = m2.group(1), m2.group(2)
    else:
        season, episode = "1", "1"

    quality = "480p"
    if "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"
    elif "2160" in up or "4K" in up:
        quality = "2k"

    return {
        "anime": anime,
        "season": f"{int(season):02d}",
        "episode": f"{int(episode):02d}",
        "quality": quality,
    }


def build_caption(info):
    return (
        f"⬡ **{info['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {info['season']}**\n"
        f"┃ **Episode : {info['episode']}**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {info['quality']}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By : {UPLOAD_TAG}**"
    )


# ======================
# BASIC COMMANDS
# ======================
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text(
        "🤖 **Anime Qualifier Bot Ready**\n\n"
        "/ping – status\n"
        "/on – enable bot (owner)\n"
        "/off – disable bot (owner)\n"
        "/set_thumb – reply photo\n"
        "/view_thumb\n"
        "/del_thumb"
    )


@app.on_message(filters.command("ping"))
async def ping(_, message: Message):
    await message.reply_text("🏓 **Pong! Bot is alive.**")


@app.on_message(filters.command("on"))
async def bot_on(_, message: Message):
    global BOT_ACTIVE
    if not is_owner(message.from_user.id):
        return
    BOT_ACTIVE = True
    await message.reply_text("✅ **Bot ENABLED**")


@app.on_message(filters.command("off"))
async def bot_off(_, message: Message):
    global BOT_ACTIVE
    if not is_owner(message.from_user.id):
        return
    BOT_ACTIVE = False
    await message.reply_text("⛔ **Bot DISABLED**")


# ======================
# THUMBNAIL (file_id based)
# ======================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, message: Message):
    global THUMB_FILE_ID
    if not is_owner(message.from_user.id):
        return
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("❌ Photo ko reply karke /set_thumb")
    THUMB_FILE_ID = message.reply_to_message.photo.file_id
    await message.reply_text("✅ **Thumbnail SET**")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, message: Message):
    if not THUMB_FILE_ID:
        return await message.reply_text("❌ No thumbnail set")
    await message.reply_photo(THUMB_FILE_ID)


@app.on_message(filters.command("del_thumb"))
async def del_thumb(_, message: Message):
    global THUMB_FILE_ID
    if not is_owner(message.from_user.id):
        return
    THUMB_FILE_ID = None
    await message.reply_text("🗑 **Thumbnail DELETED**")


# ======================
# VIDEO HANDLER (MAIN FEATURE)
# ======================
@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    if not BOT_ACTIVE:
        return
    if message.from_user.id not in OWNERS:
        return

    video = message.video or message.document
    if not video.file_name:
        return

    info = parse_video_filename(video.file_name)
    unique_key = f"{info['anime']}_{info['season']}_{info['episode']}_{info['quality']}"

    cur.execute("SELECT 1 FROM uploaded WHERE key=?", (unique_key,))
    if cur.fetchone():
        return await message.reply_text("⚠️ **Duplicate episode blocked**")

    caption = build_caption(info)
    await message.reply_text("📤 **Re-uploading to channel...**")

    await client.send_video(
        chat_id=TARGET_CHANNEL_ID,
        video=video.file_id,
        caption=caption,
        thumb=THUMB_FILE_ID,
    )

    cur.execute("INSERT INTO uploaded VALUES (?)", (unique_key,))
    db.commit()


print("🤖 Bot starting (Railway production mode)...")
app.run()
