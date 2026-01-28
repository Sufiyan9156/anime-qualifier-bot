import os
import re
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message

# ======================================================
# ENV VARIABLES (SET THESE IN RAILWAY, NOT HERE)
# ======================================================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNER_IDS = [int(i) for i in os.environ["OWNER_IDS"].split(",")]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

UPLOAD_TAG = "@SenpaiAnimess"

# ======================================================
# DATABASE (Duplicate Block + Thumbnail Storage)
# ======================================================
db = sqlite3.connect("episodes.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS uploads (
    key TEXT PRIMARY KEY
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    thumb_id TEXT
)
""")

db.commit()

# ======================================================
# BOT CLIENT
# ======================================================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ======================================================
# HELPERS
# ======================================================
def is_owner(uid: int) -> bool:
    return uid in OWNER_IDS


def parse_filename(name: str):
    n = name.replace("_", " ").replace(".", " ").upper()

    # Quality
    quality = "480p"
    if "2160" in n or "4K" in n:
        quality = "2K"
    elif "1080" in n:
        quality = "1080p"
    elif "720" in n:
        quality = "720p"

    # Season / Episode
    season, episode = "01", "01"

    m1 = re.search(r"S(\d{1,2})E(\d{1,3})", n)
    m2 = re.search(r"(\d{1,2})X(\d{1,3})", n)
    m3 = re.search(r"EP(?:ISODE)?\s*(\d{1,3})", n)

    if m1:
        season, episode = m1.group(1), m1.group(2)
    elif m2:
        season, episode = m2.group(1), m2.group(2)
    elif m3:
        episode = m3.group(1)

    season = season.zfill(2)
    episode = episode.zfill(2)

    # Anime Name
    anime = "JUJUTSU KAISEN" if "JUJUTSU" in n else "UNKNOWN ANIME"

    return {
        "anime": anime,
        "season": season,
        "episode": episode,
        "quality": quality
    }


def build_caption(info: dict) -> str:
    return (
        f"⬡ **{info['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {info['season']}**\n"
        f"┃ **Episode : {info['episode']}**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {info['quality']}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By {UPLOAD_TAG}**"
    )


def episode_key(info: dict) -> str:
    return f"{info['anime']}_S{info['season']}E{info['episode']}_{info['quality']}"


def get_thumb():
    cur.execute("SELECT thumb_id FROM settings WHERE id=1")
    row = cur.fetchone()
    return row[0] if row else None


# ======================================================
# COMMANDS
# ======================================================
@app.on_message(filters.command("ping"))
async def ping(_, m):
    await m.reply_text("🏓 **Pong! Anime Qualifier Bot is alive.**")


@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply_text("❌ Photo ke reply me /set_thumb bhejo")

    thumb_id = m.reply_to_message.photo.file_id
    cur.execute(
        "INSERT OR REPLACE INTO settings (id, thumb_id) VALUES (1, ?)",
        (thumb_id,)
    )
    db.commit()

    await m.reply_text("✅ **Thumbnail saved permanently**")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    thumb = get_thumb()
    if not thumb:
        return await m.reply_text("❌ Thumbnail set nahi hai")

    await m.reply_photo(thumb, caption="🖼 **Current Thumbnail**")


# ======================================================
# MAIN VIDEO HANDLER (RE-UPLOAD)
# ======================================================
@app.on_message((filters.video | filters.document))
async def handle_video(client, message: Message):
    if not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media.file_name:
        return

    info = parse_filename(media.file_name)
    key = episode_key(info)

    # Duplicate block
    cur.execute("SELECT 1 FROM uploads WHERE key=?", (key,))
    if cur.fetchone():
        return await message.reply_text("⛔ **Duplicate episode detected. Upload blocked.**")

    caption = build_caption(info)
    thumb = get_thumb()

    status = await message.reply_text("📤 **Re-uploading to channel...**")

    await client.send_video(
        chat_id=CHANNEL_ID,
        video=media.file_id,
        caption=caption,
        thumb=thumb,
        supports_streaming=True
    )

    cur.execute("INSERT OR IGNORE INTO uploads (key) VALUES (?)", (key,))
    db.commit()

    await status.edit_text("✅ **Upload complete & saved permanently**")


# ======================================================
# START BOT
# ======================================================
print("🤖 Anime Qualifier Bot is LIVE")
app.run()
