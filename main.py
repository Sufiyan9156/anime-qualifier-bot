import os
import re
import asyncio
from collections import defaultdict

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
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_FILE_ID = None

# queue: {(anime, season, episode): [items]}
QUEUE = defaultdict(list)

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
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"S\d+E\d+", "", name, flags=re.I)
    name = re.sub(r"\d{3,4}P.*", "", name, flags=re.I)
    name = re.sub(r"HINDI|ENG|DUAL|HDRIP|WEB[- ]?DL", "", name, flags=re.I)
    return name.strip().title()


def parse_video_filename(filename: str):
    up = filename.upper()

    anime_match = re.search(r"\]\s*(.*?)\s*S\d+E\d+", filename, re.I)
    anime_raw = anime_match.group(1) if anime_match else filename
    anime = clean_anime_name(anime_raw)

    s, e = "01", "01"
    m = re.search(r"S(\d{1,2})E(\d{1,3})", up)
    if m:
        s, e = m.group(1), m.group(2)

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
async def ping(_, m):
    await m.reply_text("✅ Anime Qualifier Bot is alive")


@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply_text("❌ Photo ko reply karke /set_thumb bhejo")
    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply_text("✅ Thumbnail set successfully")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply_text("❌ Thumbnail set nahi hai")

# =======================
# QUEUE HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media:
        return

    info = parse_video_filename(media.file_name or "video.mp4")
    key = (info["anime"], info["season"], info["episode"])

    QUEUE[key].append({
        "message": message,
        "media": media,
        "info": info
    })

    await message.reply_text(
        f"📥 Added to queue:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']} [{info['quality']}]**"
    )

    # small delay to allow bulk sends
    await asyncio.sleep(1)

    items = QUEUE.pop(key, [])
    if not items:
        return

    # sort by quality
    items.sort(key=lambda x: QUALITY_ORDER.get(x["info"]["quality"], 0))

    for item in items:
        i = item["info"]
        caption = build_caption(i)
        filename = build_filename(i)

        await client.send_video(
            chat_id=message.chat.id,
            video=item["media"].file_id,
            caption=caption,
            thumb=THUMB_FILE_ID,
            file_name=filename
        )

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot FINAL is LIVE")
app.run()
