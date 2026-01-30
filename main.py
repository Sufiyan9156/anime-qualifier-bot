import os, re, asyncio, tempfile, shutil
from telethon import TelegramClient
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
STRING_SESSION = os.environ["STRING_SESSION"]

THUMB_PATH = "thumb.jpg"

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

# ================= CLIENTS =================
user = TelegramClient(
    session=STRING_SESSION,
    api_id=API_ID,
    api_hash=API_HASH
)

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def extract_info(name: str):
    n = name.replace("_", " ").replace(".", " ").lower()

    # quality
    if "2160" in n or "4k" in n:
        q = "2k"
    elif "1080" in n:
        q = "1080p"
    elif "720" in n:
        q = "720p"
    else:
        q = "480p"

    # season / episode
    s, e = "01", "01"
    m = re.search(r"s(\d+)\s*e(\d+)", n)
    if m:
        s, e = m.group(1), m.group(2)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{int(e):03d}"

    # clean anime name
    anime = re.sub(
        r"(s\d+e\d+|\d{3,4}p|4k|hindi|dual|web|hdrip|bluray|@[\w_]+)",
        "",
        n,
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
    return f"{a} Season {s} Episode {e} ({o}) [{q}] {UPLOAD_TAG}"

# ================= THUMB =================
@bot.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karke /set_thumb bhejo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

@bot.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("❌ Thumbnail not set")

# ================= MAIN =================
@bot.on_message(filters.video | filters.document)
async def handle(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    a, s, e, o, q = extract_info(media.file_name or "video")

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "input")

    await m.reply("⬇️ Downloading fast…")
    await user.download_media(m, path)

    await bot.send_video(
        m.chat.id,
        path,
        caption=caption(a, s, e, o, q),
        file_name=fname(a, s, e, o, q),
        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
        supports_streaming=True
    )

    shutil.rmtree(tmp)

# ================= RUN =================
async def main():
    await user.start()
    await bot.start()
    print("🤖 BOT LIVE")
    await asyncio.Event().wait()

asyncio.run(main())
