import os
import re
import asyncio
import tempfile
import shutil

from telethon import TelegramClient
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
STRING_SESSION = os.environ["STRING_SESSION"].strip()

THUMB_PATH = "thumb.jpg"

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

OVERALL_OFFSET = {
    "01": 0,
    "02": 24,
    "03": 47,
    "04": 59
}

# ================= CLIENTS =================
user = TelegramClient(STRING_SESSION, API_ID, API_HASH)

bot = Client(
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

    offset = OVERALL_OFFSET.get(season, 0)
    overall = f"{offset + int(e):03d}"

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

def fname(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"

# ================= THUMB =================
@bot.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved & will apply to all uploads")

# ================= MAIN =================
@bot.on_message(filters.video | filters.document)
async def handle(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    anime, season, ep, overall, q = extract_info(media.file_name or "video")

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, fname(anime, season, ep, overall, q))

    await m.download(path)

    await bot.send_video(
        chat_id=m.chat.id,
        video=path,
        caption=caption(anime, season, ep, overall, q),
        file_name=os.path.basename(path),
        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
        supports_streaming=True
    )

    shutil.rmtree(tmp)

# ================= RUN =================
async def main():
    await user.start()
    await bot.start()
    print("🤖 Anime Qualifier Bot — FINAL STABLE BUILD LIVE")
    await asyncio.Event().wait()

asyncio.run(main())
