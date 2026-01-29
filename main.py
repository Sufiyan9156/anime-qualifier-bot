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
THUMB_FILE_ID = os.environ.get("THUMB_FILE_ID")

QUALITY_ORDER = {
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "2k": 4
}

# QUEUE[(anime, season)][episode] = [items]
QUEUE = defaultdict(lambda: defaultdict(list))
QUEUE_MSGS = defaultdict(list)
LAST_UPLOAD_TIME = {}

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
    name = name.replace("_", " ").upper()

    # remove @tags
    name = re.sub(r"@[\w\-.]+", "", name)

    # remove brackets
    name = re.sub(r"\[.*?\]", "", name)

    # remove SxxExx patterns
    name = re.sub(r"S\d+\s*E\d+", "", name)
    name = re.sub(r"S\d+E\d+", "", name)

    # remove junk words
    name = re.sub(
        r"\b(480P|720P|1080P|2160P|4K|HDRIP|WEB[- ]?DL|FHD|HD|SD|MP4|MKV|ANIME|WORLD|OFFIC|OFFICIAL)\b",
        "",
        name
    )

    name = re.sub(r"\s+", " ", name).strip()

    # keep only first 4 words (safety)
    return " ".join(name.title().split()[:4])


def parse_video_filename(filename: str):
    fixed = filename.replace("_", " ")
    up = fixed.upper()

    anime_raw = re.split(r"S\d+E\d+", fixed, flags=re.I)[0]
    anime = clean_anime_name(anime_raw)

    s, e = "01", "01"
    m = re.search(r"S(\d{1,2})\s*E(\d{1,3})", up)
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
# PROGRESS BAR
# =======================
async def progress_callback(current, total, status_msg):
    percent = current * 100 / total
    filled = int(percent // 10)
    bar = "▰" * filled + "▱" * (10 - filled)
    try:
        await status_msg.edit(
            f"📤 Uploading...\n{bar} {percent:.1f}%"
        )
    except:
        pass

# =======================
# AUTO FLUSH
# =======================
async def auto_flush(client, chat_id, key):
    await asyncio.sleep(3)

    if asyncio.get_event_loop().time() - LAST_UPLOAD_TIME.get(key, 0) < 3:
        return

    anime, season = key
    episodes = QUEUE.pop(key, {})
    msgs = QUEUE_MSGS.pop(key, [])

    for mid in msgs:
        try:
            await client.delete_messages(chat_id, mid)
        except:
            pass

    for ep in sorted(episodes.keys(), key=lambda x: int(x)):
        items = episodes[ep]
        items.sort(key=lambda x: QUALITY_ORDER[x["info"]["quality"]])

        for item in items:
            i = item["info"]

            status = await client.send_message(
                chat_id,
                f"📤 Uploading Episode {i['episode']} [{i['quality']}]..."
            )

            await client.send_video(
                chat_id=chat_id,
                video=item["media"].file_id,
                caption=build_caption(i),
                thumb=THUMB_FILE_ID,
                file_name=build_filename(i),
                supports_streaming=True,
                progress=progress_callback,
                progress_args=(status,)
            )

            await status.delete()

# =======================
# COMMANDS
# =======================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    os.environ["THUMB_FILE_ID"] = THUMB_FILE_ID
    await m.reply("✅ Thumbnail set successfully (persistent)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# =======================
# MAIN HANDLER
# =======================
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    if not media:
        return

    info = parse_video_filename(media.file_name or "video.mp4")
    key = (info["anime"], info["season"])

    QUEUE[key][info["episode"]].append({
        "media": media,
        "info": info
    })

    msg = await message.reply(
        f"📥 Added to queue:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']} [{info['quality']}]**"
    )

    QUEUE_MSGS[key].append(msg.message_id)
    LAST_UPLOAD_TIME[key] = asyncio.get_event_loop().time()

    asyncio.create_task(auto_flush(client, message.chat.id, key))

# =======================
# START
# =======================
print("🤖 Anime Qualifier Bot FINAL STABLE is LIVE")
app.run()
