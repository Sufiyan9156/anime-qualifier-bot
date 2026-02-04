import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_FILE_ID = None
QUEUE = []

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


def clean_filename(name: str) -> str:
    name = name.replace("._", "")           # macOS junk
    name = name.replace("_", " ")
    name = name.replace(".", " ")
    return re.sub(r"\s+", " ", name).strip()


def extract_info(filename: str):
    name = clean_filename(filename).lower()

    # QUALITY
    if "2160" in name or "4k" in name:
        q = "2k"
    elif "1080" in name:
        q = "1080p"
    elif "720" in name:
        q = "720p"
    else:
        q = "480p"

    # SEASON / EP
    s, e = 1, 1
    m = re.search(r"s(\d{1,2})\s*e(\d{1,3})", name)
    if m:
        s, e = int(m.group(1)), int(m.group(2))

    season = f"{s:02d}"
    episode = f"{e:02d}"
    overall = f"{e:03d}"

    anime = re.sub(
        r"(s\d+e\d+|\d{3,4}p|4k|hindi|dual|web|hdrip|bluray|mp4|mkv|@\w+)",
        "",
        name,
        flags=re.I
    )

    anime = re.sub(r"\s+", " ", anime).strip().title()

    return anime, season, episode, overall, q


def build_caption(a, s, e, o, q):
    return (
        f"⬡ **{a}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ Season : {s}\n"
        f"┃ Episode : {e}({o})\n"
        f"┃ Audio : Hindi #Official\n"
        f"┃ Quality : {q}\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ Uploaded By {UPLOAD_TAG}"
    )


def build_filename(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"


# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply("✅ Thumbnail saved (FILE_ID based)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID)
    else:
        await m.reply("❌ Thumbnail not set")


# ================= QUEUE =================
@app.on_message(filters.video | filters.document)
async def add_queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    anime, s, e, o, q = extract_info(media.file_name or "video")

    QUEUE.append({
        "file_id": media.file_id,
        "anime": anime,
        "s": s,
        "e": e,
        "o": o,
        "q": q
    })

    await m.reply(f"📥 Queued → {anime} S{s}E{e} [{q}]")


# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    await m.reply(f"🚀 Uploading {len(QUEUE)} videos...")

    while QUEUE:
        item = QUEUE.pop(0)

        path = await client.download_media(item["file_id"])

        await client.send_video(
            chat_id=m.chat.id,
            video=path,
            caption=build_caption(
                item["anime"], item["s"], item["e"], item["o"], item["q"]
            ),
            file_name=build_filename(
                item["anime"], item["s"], item["e"], item["o"], item["q"]
            ),
            thumb=THUMB_FILE_ID,
            supports_streaming=True
        )

        os.remove(path)
        await asyncio.sleep(1)

    await m.reply("✅ Done")


# ================= RUN =================
print("🤖 Anime Qualifier Bot — STABLE FIXED BUILD")
app.run()
