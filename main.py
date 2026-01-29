import os
import re
import asyncio
import tempfile
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

THUMB_FILE_ID = os.environ.get("THUMB_FILE_ID")
THUMB_PATH = "/app/custom_thumb.jpg"

QUEUE = defaultdict(list)
QUEUE_LOCKS = defaultdict(asyncio.Lock)

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
    name = name.upper()
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"S\d+E\d+", "", name)
    name = re.sub(r"\d{3,4}P", "", name)
    name = re.sub(r"HINDI|ENG|DUAL|HDRIP|WEB[- ]?DL|MP4|MKV", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()


def parse_video_filename(filename: str):
    up = filename.upper()

    anime_raw = re.split(r"S\d+E\d+", filename, flags=re.I)[0]
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
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client, m: Message):
    global THUMB_FILE_ID

    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    photo = m.reply_to_message.photo
    await client.download_media(photo.file_id, THUMB_PATH)

    THUMB_FILE_ID = photo.file_id
    os.environ["THUMB_FILE_ID"] = THUMB_FILE_ID

    await m.reply("✅ Thumbnail set successfully (persistent + local)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

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

    await message.reply(
        f"📥 Added to queue:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']} [{info['quality']}]**"
    )

    async with QUEUE_LOCKS[key]:
        await asyncio.sleep(2)

        items = QUEUE.pop(key, [])
        if not items:
            return

        items.sort(key=lambda x: QUALITY_ORDER[x["info"]["quality"]])

        for item in items:
            i = item["info"]
            caption = build_caption(i)
            filename = build_filename(i)

            tmp_dir = tempfile.mkdtemp()
            video_path = os.path.join(tmp_dir, filename)

            await item["message"].download(video_path)

            await client.send_video(
                chat_id=message.chat.id,
                video=video_path,
                caption=caption,
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                file_name=filename,
                supports_streaming=True
            )

            try:
                os.remove(video_path)
                os.rmdir(tmp_dir)
            except:
                pass

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot FINAL FIXED is LIVE")
app.run()
