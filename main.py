import os, re, asyncio
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "thumb.jpg"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

QUEUE = defaultdict(lambda: defaultdict(list))
QUEUE_MSGS = defaultdict(list)
WORKERS = set()

app = Client("anime_qualifier_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_owner(uid): return uid in OWNERS

def normalize_anime(name: str) -> str:
    name = name.replace("_", " ").replace(".", " ")
    name = re.sub(r"@[\w\-_.]+", "", name)
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"S\d+\s*E\d+.*", "", name, flags=re.I)
    name = re.sub(
        r"(480P|720P|1080P|2160P|4K|HDRIP|WEB[- ]?DL|MP4|MKV|HINDI|DUAL|WORLD|OFFIC)",
        "",
        name,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", name).strip().title()

def parse_file(filename: str):
    fixed = filename.replace("_", " ").replace(".", " ")
    up = fixed.upper()

    anime = normalize_anime(fixed)
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

def caption(i):
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

def fname(i):
    return f"{i['anime']} Season {i['season']} Episode {i['episode']} [{i['quality']}] {UPLOAD_TAG}.mp4"

async def progress(cur, tot, msg):
    p = cur * 100 / tot
    bar = "▰" * int(p // 10) + "▱" * (10 - int(p // 10))
    try:
        await msg.edit(f"📤 Uploading...\n{bar} {p:.1f}%")
    except:
        pass

async def worker(client, chat_id, key):
    await asyncio.sleep(6)

    episodes = QUEUE.pop(key, {})
    msgs = QUEUE_MSGS.pop(key, [])

    for mid in msgs:
        try: await client.delete_messages(chat_id, mid)
        except: pass

    for ep in sorted(episodes, key=lambda x: int(x)):
        items = episodes[ep]
        items.sort(key=lambda x: QUALITY_ORDER[x["info"]["quality"]])

        for it in items:
            i = it["info"]
            status = await client.send_message(chat_id, f"📤 Uploading E{i['episode']} [{i['quality']}]")

            await client.send_video(
                chat_id,
                it["media"].file_id,
                caption=caption(i),
                file_name=fname(i),
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                progress=progress,
                progress_args=(status,)
            )
            await status.delete()

    WORKERS.discard(key)

@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Reply photo with /set_thumb")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved & applied permanently")

@app.on_message(filters.video | filters.document)
async def handle(client, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    info = parse_file(media.file_name or "video.mp4")

    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"media": media, "info": info})

    r = await m.reply(f"📥 Added to queue:\n**{info['anime']} S{info['season']}E{info['episode']} [{info['quality']}]**")
    QUEUE_MSGS[key].append(r.message_id)

    if key not in WORKERS:
        WORKERS.add(key)
        asyncio.create_task(worker(client, m.chat.id, key))

print("🤖 Anime Qualifier Bot — STABLE BUILD LIVE")
app.run()
