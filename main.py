import os, re, asyncio, tempfile, shutil
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
THUMB_FILE_ID = os.environ.get("THUMB_FILE_ID")

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}
OVERALL_OFFSET = {"01": 0, "02": 24, "03": 47, "04": 59}

QUEUE = defaultdict(lambda: defaultdict(list))
ACTIVE = set()

app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HELPERS =================
def is_owner(uid): 
    return uid in OWNERS

def normalize(name: str) -> str:
    name = name.replace("_", " ").replace(".", " ")
    name = re.sub(r"@[\w\-_.]+|\[.*?\]|S\d+\s*E\d+.*", "", name, flags=re.I)
    name = re.sub(
        r"(480P|720P|1080P|2160P|4K|HDRIP|WEB|MP4|MKV|HINDI|DUAL)",
        "",
        name,
        flags=re.I
    )
    return re.sub(r"\s+", " ", name).strip().title()

def parse_file(filename: str):
    up = filename.upper()
    anime = normalize(filename)

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

    overall = OVERALL_OFFSET.get(f"{int(s):02d}", 0) + int(e)

    return {
        "anime": anime,
        "season": f"{int(s):02d}",
        "episode": f"{int(e):02d}",
        "overall": f"{overall:03d}",
        "quality": quality
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
        f"Episode {i['episode']} ({i['overall']}) "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )

# ================= COMMANDS =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    os.environ["THUMB_FILE_ID"] = THUMB_FILE_ID
    await m.reply("✅ Thumbnail saved (persistent)")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ================= WORKER =================
async def worker(client, chat_id, key):
    await asyncio.sleep(3)
    episodes = QUEUE.pop(key, {})

    for ep in sorted(episodes, key=lambda x: int(x)):
        items = sorted(
            episodes[ep],
            key=lambda x: QUALITY_ORDER[x["info"]["quality"]]
        )

        for it in items:
            i = it["info"]
            tmp = tempfile.mkdtemp()
            path = os.path.join(tmp, build_filename(i))

            await it["msg"].download(path)

            await client.send_video(
                chat_id,
                path,
                caption=build_caption(i),
                file_name=build_filename(i),
                thumb=THUMB_FILE_ID,
                supports_streaming=True
            )

            shutil.rmtree(tmp)

    ACTIVE.discard(key)

# ================= MAIN HANDLER =================
@app.on_message(filters.video | filters.document)
async def handle(client, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    info = parse_file(media.file_name or "video.mp4")

    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"msg": m, "info": info})

    await m.reply(
        f"📥 Added to queue:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']}({info['overall']}) [{info['quality']}]**"
    )

    if key not in ACTIVE:
        ACTIVE.add(key)
        asyncio.create_task(worker(client, m.chat.id, key))

print("🤖 Anime Qualifier Bot — FINAL STABLE & CORRECT BUILD")
app.run()
