import os, re, asyncio, tempfile, shutil, time
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from telethon import TelegramClient
from telethon.tl.types import Message as TLMessage

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
ACTIVE = False

# ================= CLIENTS =================
bot = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user = TelegramClient(
    "user",  # user.session
    API_ID,
    API_HASH
)

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

    return {
        "anime": clean_anime_name(filename),
        "season": f"{int(s):02d}",
        "episode": f"{int(e):02d}",
        "overall": f"{int(e):03d}",
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
@bot.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    os.environ["THUMB_FILE_ID"] = THUMB_FILE_ID
    await m.reply("✅ Thumbnail saved permanently")

@bot.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ================= PREVIEW =================
@bot.on_message(filters.command("preview"))
async def preview(_, m):
    if not is_owner(m.from_user.id) or not QUEUE:
        return

    text = "📋 **Upload Preview**\n\n"
    for (anime, season), eps in QUEUE.items():
        text += f"**{anime} – Season {season}**\n"
        for ep in sorted(eps):
            qs = ", ".join(x["info"]["quality"] for x in eps[ep])
            text += f"Episode {ep} → {qs}\n"
        text += "\n"

    await m.reply(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Start Upload", callback_data="start")]]
        )
    )

# ================= CALLBACK =================
@bot.on_callback_query()
async def cb(_, q):
    global ACTIVE
    if q.data == "start" and not ACTIVE:
        ACTIVE = True
        await q.message.edit("🚀 Upload started...")
        asyncio.create_task(worker(q.message.chat.id))
        await q.answer()

# ================= WORKER =================
async def worker(chat_id):
    global ACTIVE
    tmp = tempfile.mkdtemp()

    async with user:
        for (_, _), eps in list(QUEUE.items()):
            for ep in sorted(eps):
                for it in sorted(eps[ep], key=lambda x: QUALITY_ORDER[x["info"]["quality"]]):
                    i = it["info"]
                    msg: TLMessage = await user.get_messages(
                        it["msg"].chat.id,
                        ids=it["msg"].id
                    )

                    vpath = os.path.join(tmp, build_filename(i))
                    await msg.download_media(vpath)

                    await bot.send_video(
                        chat_id,
                        vpath,
                        caption=build_caption(i),
                        file_name=build_filename(i),
                        thumb=THUMB_FILE_ID,
                        supports_streaming=True
                    )

                    os.remove(vpath)

    shutil.rmtree(tmp)
    QUEUE.clear()
    ACTIVE = False
    await bot.send_message(chat_id, "✅ All uploads completed")

# ================= MAIN =================
@bot.on_message(filters.video | filters.document)
async def handle(_, m):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    info = extract_info((m.video or m.document).file_name or "video")
    QUEUE[(info["anime"], info["season"])][info["episode"]].append(
        {"msg": m, "info": info}
    )

    await m.reply(
        f"📥 Added:\n"
        f"**{info['anime']} Season {info['season']} "
        f"Episode {info['episode']} ({info['overall']}) "
        f"[{info['quality']}]**"
    )

print("🤖 Hybrid Telethon USER + Bot running")
bot.run()
