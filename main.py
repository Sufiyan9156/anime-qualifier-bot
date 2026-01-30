import os
import re
import asyncio
import tempfile
import shutil

from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

THUMB_PATH = "thumb.jpg"

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

OVERALL_OFFSET = {
    "01": 0,
    "02": 24,
    "03": 47,
    "04": 59
}

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HELPERS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS

def extract_info(filename: str):
    name = filename.replace("_", " ").replace(".", " ")
    up = name.upper()

    # Quality
    if "2160" in up or "4K" in up:
        q = "2k"
    elif "1080" in up:
        q = "1080p"
    elif "720" in up:
        q = "720p"
    else:
        q = "480p"

    # Season / Episode
    s, e = "01", "01"
    m = re.search(r"S(\d{1,2})\s*E(\d{1,3})", up)
    if m:
        s, e = m.group(1), m.group(2)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{OVERALL_OFFSET.get(season, 0) + int(e):03d}"

    anime = re.sub(
        r"(S\d+E\d+|\d{3,4}P|4K|HINDI|DUAL|WEB|HDRIP|BLURAY|MP4|MKV|@[\w_]+)",
        "",
        name,
        flags=re.I
    )
    anime = re.sub(r"\s+", " ", anime).strip().title()

    return anime, season, episode, overall, q

def caption(a, s, e, o, q):
    return (
        f"⬡ **{a}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {s}**\n"
        f"┃ **Episode : {e}({o})**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {q}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By {UPLOAD_TAG}**"
    )

def filename(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved & will apply to all uploads")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail not set")

# ================= MAIN =================
@app.on_message(filters.video | filters.document)
async def handle(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    anime, season, ep, overall, q = extract_info(media.file_name or "video")

    tmp = tempfile.mkdtemp()
    out_path = os.path.join(tmp, filename(anime, season, ep, overall, q))

    await m.download(out_path)

    await app.send_video(
        chat_id=m.chat.id,
        video=out_path,
        caption=caption(anime, season, ep, overall, q),
        file_name=os.path.basename(out_path),
        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
        supports_streaming=True
    )

    shutil.rmtree(tmp)

# ================= RUN =================
print("🤖 Anime Qualifier Bot — STABLE & CRASH-FREE")
app.run()
