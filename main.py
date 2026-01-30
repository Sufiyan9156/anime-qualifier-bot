import os, re, asyncio, tempfile, shutil, time
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

THUMB_PATH = "thumb.jpg"

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}
QUEUE = defaultdict(lambda: defaultdict(list))
ACTIVE = False

app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= PROGRESS =================
async def progress(current, total, msg, start, label):
    if total == 0:
        return
    percent = int(current * 100 / total)
    speed = current / max(1, time.time() - start)
    try:
        await msg.edit(
            f"{label}\n"
            f"{percent}% | {speed/1024/1024:.2f} MB/s"
        )
    except:
        pass

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def clean_anime_name(name: str):
    name = name.replace("_", " ").replace(".", " ")

    name = re.sub(r"\[.*?\]|\(.*?\)", " ", name)
    name = re.sub(r"@[\w_]+", " ", name)

    REMOVE = [
        "mp4","mkv","avi","hd","fhd","uhd","sd",
        "hindi","dual","multi","audio","official",
        "world","web","hdrip","bluray","360p","720p","1080p","2160p","4k"
    ]

    for r in REMOVE:
        name = re.sub(rf"\b{r}\b", " ", name, flags=re.I)

    name = re.sub(r"S\d+\s*E\d+|SEASON\s*\d+|EPISODE\s*\d+", " ", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()

    return name.title()

def extract_info(filename: str):
    raw = filename.lower()

    if re.search(r"(2160|4k|uhd)", raw):
        quality = "2k"
    elif re.search(r"(1080|fhd)", raw):
        quality = "1080p"
    elif re.search(r"(720|hd)", raw):
        quality = "720p"
    else:
        quality = "480p"

    s, e = "01", "01"
    m = re.search(r"s(\d{1,2})\s*e(\d{1,3})", raw)
    if m:
        s, e = m.group(1), m.group(2)
    else:
        m = re.search(r"episode\s*(\d{1,3})", raw)
        if m:
            e = m.group(1)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{int(e):03d}"

    anime = clean_anime_name(filename)

    return {
        "anime": anime,
        "season": season,
        "episode": episode,
        "overall": overall,
        "quality": quality
    }

def build_filename(i):
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']} ({i['overall']}) "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )

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

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved permanently")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m):
    if not is_owner(m.from_user.id) or not QUEUE:
        return

    text = "📋 **Upload Preview**\n\n"
    for (anime, season), eps in QUEUE.items():
        text += f"**{anime} – Season {season}**\n"
        for ep in sorted(eps, key=lambda x: int(x)):
            qs = ", ".join(
                x["info"]["quality"]
                for x in sorted(eps[ep], key=lambda y: QUALITY_ORDER[y["info"]["quality"]])
            )
            text += f"Episode {ep} → {qs}\n"
        text += "\n"

    await m.reply(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Start Upload", callback_data="start")]]
        )
    )

# ================= CALLBACK =================
@app.on_callback_query()
async def cb(client, q):
    global ACTIVE
    if q.data == "start" and not ACTIVE:
        ACTIVE = True
        await q.message.edit("🚀 Upload started...")
        asyncio.create_task(worker(client, q.message.chat.id))
        await q.answer()

# ================= WORKER =================
async def worker(client, chat_id):
    global ACTIVE
    tmp = tempfile.mkdtemp()

    for (_, _), eps in list(QUEUE.items()):
        for ep in sorted(eps, key=lambda x: int(x)):
            for it in sorted(eps[ep], key=lambda x: QUALITY_ORDER[x["info"]["quality"]]):
                i = it["info"]

                status = await client.send_message(chat_id, "⬇️ Downloading...")
                start = time.time()

                vpath = os.path.join(tmp, build_filename(i))
                await it["msg"].download(
                    vpath,
                    progress=progress,
                    progress_args=(status, start, "⬇️ Downloading")
                )

                start_up = time.time()
                await client.send_video(
                    chat_id,
                    vpath,
                    caption=build_caption(i),
                    file_name=build_filename(i),
                    thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                    supports_streaming=True,
                    progress=progress,
                    progress_args=(status, start_up, "⬆️ Uploading")
                )

                await status.delete()
                os.remove(vpath)

    shutil.rmtree(tmp)
    QUEUE.clear()
    ACTIVE = False
    await client.send_message(chat_id, "✅ All uploads completed")

# ================= MAIN =================
@app.on_message(filters.video | filters.document)
async def handle(_, m):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    info = extract_info((m.video or m.document).file_name or "video")
    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"msg": m, "info": info})

    await m.reply(
        f"📥 Added:\n"
        f"**{info['anime']} Season {info['season']} "
        f"Episode {info['episode']} ({info['overall']}) "
        f"[{info['quality']}]**"
    )

print("🤖 Anime Qualifier Bot — FINAL CLEAN STABLE BUILD")
app.run()
