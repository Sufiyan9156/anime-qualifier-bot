import os
import re
import asyncio
from collections import defaultdict

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

# in-memory thumb (Railway restart = reset, expected)
THUMB_FILE_ID = None

# batch buffer
BATCH = defaultdict(list)
BATCH_LOCK = asyncio.Lock()

# quality priority
QUALITY_ORDER = {
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "2k": 4
}

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


def clean_anime_name(name: str) -> str:
    """
    Removes quality / junk words from anime name
    """
    name = name.upper()

    # remove common junk
    junk = [
        r"\b\d{3,4}P\b",
        r"\bHD\b", r"\bFHD\b", r"\bSD\b",
        r"\bHDRIP\b", r"\bWEB\b", r"\bMP4\b",
        r"\bHINDI\b", r"\bDUAL\b",
        r"\bS\d+E\d+\b",
        r"\bEPISODE\b", r"\bEP\b"
    ]

    for j in junk:
        name = re.sub(j, "", name)

    name = re.sub(r"[\[\]\(\)_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name.title() if name else "Unknown"


def parse_video_filename(filename: str):
    up = filename.upper()

    # season & episode
    season, episode = "01", "01"
    m = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    if m:
        season, episode = m.group(1), m.group(2)

    # quality
    if "2160" in up or "4K" in up:
        quality = "2k"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"
    else:
        quality = "480p"

    anime = clean_anime_name(filename)

    return {
        "anime": anime,
        "season": f"{int(season):02d}",
        "episode": f"{int(episode):02d}",
        "quality": quality
    }


def build_caption(info: dict) -> str:
    return (
        f"**⬡ {info['anime']}**\n"
        f"**┏━━━━━━━━━━━━━━━━━━┓**\n"
        f"**┃ Season : {info['season']}**\n"
        f"**┃ Episode : {info['episode']}**\n"
        f"**┃ Audio : Hindi #Official**\n"
        f"**┃ Quality : {info['quality']}**\n"
        f"**┗━━━━━━━━━━━━━━━━━━┛**\n"
        f"**⬡ Uploaded By {UPLOAD_TAG}**"
    )


def build_filename(info: dict) -> str:
    return (
        f"{info['anime']} Season {info['season']} "
        f"Episode {info['episode']} "
        f"[{info['quality']}] {UPLOAD_TAG}.mp4"
    )

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("ping"))
async def ping(_, m: Message):
    await m.reply_text("✅ Anime Qualifier Bot is alive")


@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID

    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply("✅ Thumbnail set successfully")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# =======================
# MAIN HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media or not media.file_name:
        return

    info = parse_video_filename(media.file_name)

    key = (message.chat.id, info["anime"], info["season"], info["episode"])

    async with BATCH_LOCK:
        BATCH[key].append((info, media.file_id))

    await message.reply_text(f"📦 Added {info['quality']}")

    # small delay to allow multiple qualities
    await asyncio.sleep(2)

    async with BATCH_LOCK:
        items = BATCH.pop(key, [])

    if not items:
        return

    # sort by quality
    items.sort(key=lambda x: QUALITY_ORDER[x[0]["quality"]])

    for info, file_id in items:
        caption = build_caption(info)
        filename = build_filename(info)

        await client.send_video(
            chat_id=message.chat.id,
            video=file_id,
            caption=caption,
            file_name=filename,
            thumb=THUMB_FILE_ID
        )

    await message.reply_text("✅ Video processed & sent back")

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE (Final Stable Version)")
app.run()
