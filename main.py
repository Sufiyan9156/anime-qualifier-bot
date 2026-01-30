import os, re, asyncio, tempfile, shutil
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
THUMB_FILE_ID = os.environ.get("THUMB_FILE_ID")

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

QUEUE = defaultdict(lambda: defaultdict(list))

app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def extract_info(filename: str):
    name = filename.replace("_", " ").replace(".", " ")

    # QUALITY
    quality = "480p"
    if re.search(r"(2160|4K)", name, re.I):
        quality = "2k"
    elif re.search(r"1080", name, re.I):
        quality = "1080p"
    elif re.search(r"720", name, re.I):
        quality = "720p"

    # SEASON & EPISODE
    s, e = "01", "01"
    m = re.search(r"S(\d{1,2})\s*E(\d{1,3})", name, re.I)
    if m:
        s, e = m.group(1), m.group(2)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{int(e):03d}"

    # CLEAN ANIME NAME
    anime = re.sub(
        r"(S\d+\s*E\d+|EPISODE\s*\d+|\d{3,4}P|SD|HDRIP|WEB|HINDI|DUAL|\[.*?\]|@[\w_]+)",
        "",
        name,
        flags=re.I
    )
    anime = re.sub(r"\s+", " ", anime).strip().title()

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
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    os.environ["THUMB_FILE_ID"] = THUMB_FILE_ID
    await m.reply("✅ Thumbnail saved")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m):
    if not is_owner(m.from_user.id):
        return

    if not QUEUE:
        return await m.reply("❌ Queue empty")

    text = "📋 **Upload Preview**\n\n"
    for (anime, season), eps in QUEUE.items():
        text += f"**{anime} – Season {season}**\n"
        for ep in sorted(eps):
            text += f"Episode {ep} ({eps[ep][0]['info']['overall']})\n"
            for it in sorted(eps[ep], key=lambda x: QUALITY_ORDER[x["info"]["quality"]]):
                text += f" • {it['info']['quality']}\n"
        text += "\n"

    await m.reply(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Start Upload", callback_data="start")]
        ])
    )

# ================= CALLBACK =================
@app.on_callback_query()
async def cb(client, q):
    if q.data == "start":
        key = list(QUEUE.keys())[0]
        await q.message.edit("🚀 Upload started...")
        asyncio.create_task(worker(client, q.message.chat.id, key))

# ================= WORKER =================
async def worker(client, chat_id, key):
    episodes = QUEUE.pop(key)

    for ep in sorted(episodes):
        for it in sorted(episodes[ep], key=lambda x: QUALITY_ORDER[x["info"]["quality"]]):
            i = it["info"]
            tmp = tempfile.mkdtemp()
            vpath = os.path.join(tmp, build_filename(i))

            await it["msg"].download(vpath)

            thumb = None
            if THUMB_FILE_ID:
                thumb = os.path.join(tmp, "thumb.jpg")
                await client.download_media(THUMB_FILE_ID, thumb)

            await client.send_video(
                chat_id,
                vpath,
                caption=build_caption(i),
                file_name=build_filename(i),
                thumb=thumb,
                supports_streaming=True
            )

            shutil.rmtree(tmp)

# ================= MAIN =================
@app.on_message(filters.video | filters.document)
async def handle(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    info = extract_info((m.video or m.document).file_name or "video.mp4")
    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"msg": m, "info": info})

    await m.reply(
        f"📥 Added:\n"
        f"**{build_filename(info)}**"
    )

print("🤖 Anime Qualifier Bot — NAMING PERFECT BUILD")
app.run()
