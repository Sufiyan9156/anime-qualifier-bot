import os, re, asyncio, tempfile, shutil
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}
OVERALL_OFFSET = {"01": 0, "02": 24, "03": 47, "04": 59}

THUMB_PATH = "/app/thumb.jpg"

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
    name = re.sub(r"@[\w\-_.]+|\[.*?\]", "", name)
    name = re.sub(r"(480P|720P|1080P|2160P|4K|HDRIP|WEB|MP4|MKV|HINDI|DUAL)", "", name, flags=re.I)
    name = re.sub(r"(S(?:EASON)?\s*\d+|E(?:P|PISODE)?\s*\d+)", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).strip().title()

def parse_file(filename: str):
    up = filename.upper()

    # QUALITY
    quality = "480p"
    if "2160" in up or "4K" in up:
        quality = "2k"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"

    # SEASON
    season = "01"
    sm = re.search(r"S(?:EASON)?\s*0?(\d{1,2})", up)
    if sm:
        season = f"{int(sm.group(1)):02d}"

    # EPISODE (STRICT)
    em = re.search(r"(?:E|EP|EPISODE)[\s._-]*0?(\d{1,3})", up)
    if not em:
        raise ValueError("Episode number not found")

    episode = f"{int(em.group(1)):02d}"

    overall = OVERALL_OFFSET.get(season, 0) + int(episode)

    anime = normalize(filename)

    return {
        "anime": anime,
        "season": season,
        "episode": episode,
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

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved & will apply on all uploads")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.isfile(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail set nahi hai")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m):
    if not is_owner(m.from_user.id):
        return

    if not QUEUE:
        return await m.reply("❌ Queue empty")

    text = "📋 **Upload Order Preview**\n\n"
    for (anime, season), eps in sorted(QUEUE.items()):
        for ep in sorted(eps, key=lambda x: int(x)):
            text += f"**{anime} S{season}E{ep}({eps[ep][0]['info']['overall']})**\n"
            for it in sorted(eps[ep], key=lambda x: QUALITY_ORDER[x["info"]["quality"]]):
                text += f" • {it['info']['quality']}\n"
            text += "\n"

    await m.reply(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Start Upload", callback_data="start")],
            [InlineKeyboardButton("❌ Clear Queue", callback_data="clear")]
        ])
    )

# ================= CALLBACK =================
@app.on_callback_query()
async def callbacks(client, q):
    if not is_owner(q.from_user.id):
        return

    if q.data == "clear":
        QUEUE.clear()
        await q.message.edit("❌ Queue cleared")

    elif q.data == "start":
        await q.message.edit("🚀 Upload started...")
        key = list(QUEUE.keys())[0]
        asyncio.create_task(worker(client, q.message.chat.id, key))

# ================= WORKER =================
async def worker(client, chat_id, key):
    episodes = QUEUE.pop(key)

    for ep in sorted(episodes, key=lambda x: int(x)):
        items = sorted(episodes[ep], key=lambda x: QUALITY_ORDER[x["info"]["quality"]])

        for it in items:
            i = it["info"]
            tmp = tempfile.mkdtemp()
            vpath = os.path.join(tmp, build_filename(i))

            await it["msg"].download(vpath)

            await client.send_video(
                chat_id,
                vpath,
                caption=build_caption(i),
                file_name=build_filename(i),
                thumb=THUMB_PATH if os.path.isfile(THUMB_PATH) else None,
                supports_streaming=True
            )

            shutil.rmtree(tmp)

    await client.send_message(chat_id, "✅ All uploads completed")

# ================= MAIN =================
@app.on_message(filters.video | filters.document)
async def handle(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    try:
        info = parse_file((m.video or m.document).file_name or "")
    except:
        return await m.reply(
            "❌ Episode number filename me nahi mila.\n"
            "Example: JJK S01 E24 720p.mp4"
        )

    key = (info["anime"], info["season"])
    QUEUE[key][info["episode"]].append({"msg": m, "info": info})

    await m.reply(
        f"📥 Added:\n"
        f"**{info['anime']} S{info['season']}E{info['episode']}({info['overall']}) [{info['quality']}]**"
    )

print("🤖 Anime Qualifier Bot — FINAL CLEAN BUILD")
app.run()
