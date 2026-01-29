import os
import re
import asyncio
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_FILE_ID = os.environ.get("THUMB_FILE_ID")

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

QUEUE = defaultdict(lambda: defaultdict(list))
QUEUE_MSGS = defaultdict(list)
WORKERS_RUNNING = set()

app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

def is_owner(uid: int) -> bool:
    return uid in OWNERS


def clean_anime_name(name: str) -> str:
    name = name.replace("_", " ")
    name = re.sub(r"@[\w\-_.]+", "", name)
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"S\d+\s*E\d+", "", name, flags=re.I)
    name = re.sub(
        r"(480P|720P|1080P|2160P|4K|HDRIP|WEB[- ]?DL|MP4|MKV|ANIME|WORLD|OFFIC|OFFICIAL)",
        "",
        name,
        flags=re.I,
    )
    name = re.sub(r"\s+", " ", name).strip()
    return " ".join(name.title().split()[:4])


def parse_video_filename(filename: str):
    fixed = filename.replace("_", " ")
    up = fixed.upper()

    anime = clean_anime_name(re.split(r"S\d+E\d+", fixed, flags=re.I)[0])

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
        "quality": quality,
    }


def build_caption(i):
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


def build_filename(i):
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']} "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )


async def progress_cb(current, total, msg):
    pct = current * 100 / total
    bar = "▰" * int(pct // 10) + "▱" * (10 - int(pct // 10))
    try:
        await msg.edit(f"📤 Uploading...\n{bar} {pct:.1f}%")
    except:
        pass


async def queue_worker(client, chat_id, key):
    await asyncio.sleep(8)

    anime, season = key
    episodes = QUEUE.pop(key, {})
    msgs = QUEUE_MSGS.pop(key, [])

    for mid in msgs:
        try:
            await client.delete_messages(chat_id, mid)
        except:
            pass

    for ep in sorted(episodes, key=lambda x: int(x)):
        items = episodes[ep]
        items.sort(key=lambda x: QUALITY_ORDER[x["info"]["quality"]])

        for item in items:
            i = item["info"]
            status = await client.send_message(
                chat_id, f"📤 Uploading Episode {i['episode']} [{i['quality']}]"
            )

            await client.send_video(
                chat_id,
                item["media"].file_id,
                caption=build_caption(i),
                thumb=THUMB_FILE_ID,
                file_name=build_filename(i),
                supports_streaming=True,
                progress=progress_cb,
                progress_args=(status,),
            )
            await status.delete()

    WORKERS_RUNNING.discard(key)


@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    media = message.video or message.document
    info = parse_video_filename(media.file_name or "video.mp4")

    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"media": media, "info": info})

    m = await message.reply(
        f"📥 Added to queue:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']} [{info['quality']}]**"
    )
    QUEUE_MSGS[key].append(m.message_id)

    if key not in WORKERS_RUNNING:
        WORKERS_RUNNING.add(key)
        asyncio.create_task(queue_worker(client, message.chat.id, key))


print("🤖 Anime Qualifier Bot — FINAL WORKING BUILD LIVE")
app.run()
