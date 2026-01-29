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

# quality sort order
QUALITY_ORDER = {
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "2k": 4
}

# in-memory stores
BATCH = {}        # {(anime, season, episode): [media]}
THUMBS = {}       # {anime: thumb_file_id}

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


def detect_anime_name(filename: str):
    name = filename.upper()

    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"@\w+", "", name)
    name = re.sub(
        r"\b(360P|480P|720P|1080P|2160P|4K|HDRIP|HD|FHD|SD)\b",
        "",
        name
    )
    name = re.sub(r"S\d{1,2}E\d{1,3}", "", name)
    name = re.sub(r"[_\-\.]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name.title() if name else "Unknown"


def parse_video_filename(name: str):
    up = name.upper()

    anime = detect_anime_name(name)

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


def build_filename(i):
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']} "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )


async def flush_batch(client: Client, chat_id, key):
    videos = BATCH.pop(key, [])

    videos.sort(key=lambda x: QUALITY_ORDER.get(x["info"]["quality"], 99))

    for item in videos:
        info = item["info"]
        media = item["media"]

        caption = build_caption(info)
        filename = build_filename(info)
        thumb = THUMBS.get(info["anime"])

        await client.send_video(
            chat_id=chat_id,
            video=media.file_id,
            caption=caption,
            file_name=filename,
            thumb=thumb
        )

        await asyncio.sleep(1)


# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("ping"))
async def ping(_, m):
    await m.reply_text("✅ Anime Qualifier Bot is alive")


@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    anime = detect_anime_name(m.reply_to_message.caption or "")
    THUMBS[anime] = m.reply_to_message.photo.file_id

    await m.reply(f"✅ Thumbnail set for **{anime}**")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if not THUMBS:
        return await m.reply("❌ Thumbnail set nahi hai")

    for anime, fid in THUMBS.items():
        await m.reply_photo(fid, caption=f"🖼 {anime}")


# =======================
# MAIN HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media or not media.file_name:
        return

    info = parse_video_filename(media.file_name)
    key = (info["anime"], info["season"], info["episode"])

    if key not in BATCH:
        BATCH[key] = []

    BATCH[key].append({
        "media": media,
        "info": info
    })

    await message.reply(
        f"📥 Added `{info['quality']}`\n"
        f"📦 Batch: {info['anime']} S{info['season']}E{info['episode']}"
    )

    await asyncio.sleep(2)
    await flush_batch(client, message.chat.id, key)


# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot is LIVE (Final Build)")
app.run()
