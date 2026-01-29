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

# =======================
# DATABASE
# =======================
db = sqlite3.connect("episodes.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS episodes (
    key TEXT PRIMARY KEY
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    k TEXT PRIMARY KEY,
    v TEXT
)
""")
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
def is_owner(uid: int) -> bool:
    return uid in OWNERS


def get_thumb():
    cur.execute("SELECT v FROM settings WHERE k='thumb'")
    r = cur.fetchone()
    return r[0] if r else None


def set_thumb_db(fid):
    cur.execute("INSERT OR REPLACE INTO settings VALUES ('thumb', ?)", (fid,))
    db.commit()


def parse_video_filename(name: str):
    up = name.upper()

    anime = "JUJUTSU KAISEN" if "JUJUTSU" in up else "UNKNOWN"

    s, e = "01", "01"
    m1 = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    m2 = re.search(r"(\d{1,2})X(\d{1,3})", up)

    if m1:
        s, e = m1.group(1), m1.group(2)
    elif m2:
        s, e = m2.group(1), m2.group(2)

    quality = "480p"
    if "2160" in up or "4K" in up:
        quality = "2k"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"

    return {
        "anime": anime,
        "season": f"{int(s):02d}",
        "episode": f"{int(e):02d}",
        "quality": quality
    }


def build_caption(i: dict) -> str:
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


def episode_key(i: dict) -> str:
    return f"{i['anime']}_S{i['season']}E{i['episode']}_{i['quality']}"

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("ping"))
async def ping(_, m):
    await m.reply_text("🏓 Anime Qualifier Bot is alive!")


@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("❌ Photo ko reply karke /set_thumb bhejo")

    set_thumb_db(m.reply_to_message.photo.file_id)
    await m.reply_text("✅ Thumbnail permanently saved")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    fid = get_thumb()
    if fid:
        await m.reply_photo(fid, caption="🖼 Current Thumbnail")
    else:
        await m.reply_text("❌ Thumbnail set nahi hai")

# =======================
# REUPLOAD HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def reupload(client, message: Message):
    try:
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
            return await message.reply_text("⛔ Duplicate episode detected")

        caption = build_caption(info)
        status = await message.reply_text("📤 Re-uploading to channel...")

        await client.send_video(
            chat_id=TARGET_CHANNEL_ID,
            video=media.file_id,
            caption=caption,
            thumb=get_thumb()
        )

        cur.execute("INSERT OR IGNORE INTO episodes VALUES (?)", (key,))
        db.commit()

        await status.edit_text("✅ Upload successful")

    except Exception as e:
        print("❌ ERROR:", e)
        await message.reply_text(f"❌ Error: {e}")

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE")
app.run()
