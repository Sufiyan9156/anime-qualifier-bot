import os, re, asyncio, tempfile, shutil
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "thumb.jpg"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

# Season → overall offset
OVERALL_OFFSET = {
    "01": 0,
    "02": 24,
    "03": 47,
    "04": 59,
}

QUEUE = defaultdict(lambda: defaultdict(list))
QUEUE_MSGS = defaultdict(list)
ACTIVE_WORKERS = set()

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def normalize_anime(name: str) -> str:
    name = name.replace("_", " ").replace(".", " ")
    name = re.sub(r"@[\w\-_.]+", "", name)
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"S\d+\s*E\d+.*", "", name, flags=re.I)
    name = re.sub(
        r"(480P|720P|1080P|2160P|4K|HDRIP|WEB[- ]?DL|MP4|MKV|HINDI|DUAL)",
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

    offset = OVERALL_OFFSET.get(f"{int(s):02d}", 0)
    overall = offset + int(e)

    return {
        "anime": anime,
        "season": f"{int(s):02d}",
        "episode": f"{int(e):02d}",
        "overall": f"{overall:03d}",
        "quality": quality,
    }

def build_caption(i):
    return (
        f"⬡ **{i['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {i['season']}**\n"
        f"┃ **Episode : {i['episode']}({i['overall']})**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {i['quality']}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By {UPLOAD_TAG}**"
    )

def build_filename(i):
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']}({i['overall']}) "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )

async def progress(cur, tot, msg):
    if tot == 0:
        return
    p = cur * 100 / tot
    bar = "▰" * int(p // 10) + "▱" * (10 - int(p // 10))
    try:
        await msg.edit(f"📤 Uploading...\n{bar} {p:.1f}%")
    except:
        pass

# ================= WORKER =================
async def worker(client, chat_id, key):
    await asyncio.sleep(4)

    episodes = QUEUE.pop(key, {})
    msgs = QUEUE_MSGS.pop(key, [])

    for mid in msgs:
        try:
            await client.delete_messages(chat_id, mid)
        except:
            pass

    try:
        for ep in sorted(episodes, key=lambda x: int(x)):
            items = episodes[ep]
            items.sort(key=lambda x: QUALITY_ORDER[x["info"]["quality"]])

            for it in items:
                info = it["info"]

                status = await client.send_message(
                    chat_id,
                    f"📤 Uploading Episode {info['episode']}({info['overall']}) [{info['quality']}]"
                )

                tmpdir = tempfile.mkdtemp()
                filepath = os.path.join(tmpdir, build_filename(info))

                await it["message"].download(filepath)

                await client.send_video(
                    chat_id=chat_id,
                    video=filepath,
                    caption=build_caption(info),
                    file_name=build_filename(info),
                    thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                    supports_streaming=True,
                    progress=progress,
                    progress_args=(status,)
                )

                await status.delete()
                shutil.rmtree(tmpdir, ignore_errors=True)

    finally:
        ACTIVE_WORKERS.discard(key)

# ================= COMMANDS =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved & will apply on all uploads")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ================= MAIN HANDLER =================
@app.on_message(filters.video | filters.document)
async def handle(client, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    info = parse_file(media.file_name or "video.mp4")

    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"message": m, "info": info})

    reply = await m.reply(
        f"📥 Added to queue:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']}({info['overall']}) [{info['quality']}]**"
    )

    QUEUE_MSGS[key].append(reply.id)

    if key not in ACTIVE_WORKERS:
        ACTIVE_WORKERS.add(key)
        asyncio.create_task(worker(client, m.chat.id, key))

print("🤖 Anime Qualifier Bot — STABLE & CORRECT BUILD LIVE")
app.run()
