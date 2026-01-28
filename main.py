import os
import re
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message

# =======================
# ENV (Railway)
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

BOT_ACTIVE = True
THUMB_FILE_ID = None

# =======================
# DATABASE (Duplicate Block)
# =======================
db = sqlite3.connect("episodes.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS episodes (
    key TEXT PRIMARY KEY
)
""")
db.commit()

# =======================
# BOT CLIENT
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

    anime = "JUJUTSU KAISEN" if "JUJUTSU" in up else "UNKNOWN"

    season, episode = "01", "01"

    m1 = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    m2 = re.search(r"(\d{1,2})X(\d{1,3})", up)

    if m1:
        season, episode = m1.group(1), m1.group(2)
    elif m2:
        season, episode = m2.group(1), m2.group(2)

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


def build_caption(info: dict) -> str:
    return (
        f"⬡ **{info['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ Season : {info['season']}\n"
        f"┃ Episode : {info['episode']}\n"
        f"┃ Audio : Hindi #Official\n"
        f"┃ Quality : {info['quality']}\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ Uploaded By {UPLOAD_TAG}"
    )


def episode_key(info: dict) -> str:
    return f"{info['anime']}_S{info['season']}E{info['episode']}_{info['quality']}"

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("ping"))
async def ping(_, m):
    await m.reply_text("✅ Anime Qualifier Bot is alive!")


@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID

    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text(
            "❌ Photo ko reply karke /set_thumb bhejo\n\n"
            "Step:\n"
            "1) Photo bhejo\n"
            "2) Us photo ke reply me /set_thumb"
        )

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply_text("✅ Thumbnail SET successfully")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply_text("❌ Thumbnail set nahi hai")

# =======================
# MAIN RE-UPLOAD HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def reupload(client, message: Message):
    if not BOT_ACTIVE:
        return

    if not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    file_name = media.file_name or "video.mp4"

    info = parse_video_filename(file_name)
    key = episode_key(info)

    cur.execute("SELECT key FROM episodes WHERE key=?", (key,))
    if cur.fetchone():
        await message.reply_text("⛔ Duplicate episode detected. Upload blocked.")
        return

    caption = build_caption(info)
    status = await message.reply_text("📤 Re-uploading to channel...")

    await client.send_video(
        chat_id=TARGET_CHANNEL_ID,
        video=media.file_id,
        caption=caption,
        thumb=THUMB_FILE_ID
    )

    cur.execute("INSERT OR IGNORE INTO episodes VALUES (?)", (key,))
    db.commit()

    await status.edit_text("✅ Upload complete & saved")

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE")
app.run()
