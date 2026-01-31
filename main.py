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

# ================= GLOBALS =================
THUMB_FILE_ID = None
QUEUE = []                 # bulk upload queue
LAST_PREVIEW = {}          # chat_id -> last uploaded message_id

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

    # -------- Quality --------
    if "2160" in up or "4K" in up:
        quality = "2k"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"
    else:
        quality = "480p"

    # -------- Season / Episode --------
    s, e = "01", "01"
    m = re.search(r"S(\d{1,2})\s*E(\d{1,3})", up)
    if m:
        s, e = m.group(1), m.group(2)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{int(e):03d}"

    # -------- Anime name clean --------
    anime = re.sub(
        r"(S\d+E\d+|\d{3,4}P|4K|HINDI|DUAL|WEB|HDRIP|BLURAY|@[\w_]+)",
        "",
        name,
        flags=re.I
    )
    anime = re.sub(r"\s+", " ", anime).strip().title()

    return anime, season, episode, overall, quality


def build_caption(a, s, e, o, q):
    return (
        f"⬡ **{a}**\n"
        f"╭━━━━━━━━━━━━━━━━━━\n"
        f"‣ Season : {s}\n"
        f"‣ Episode : {e}({o})\n"
        f"‣ Audio : Hindi #Official\n"
        f"‣ Quality : {q}\n"
        f"╰━━━━━━━━━━━━━━━━━━\n"
        f"⬡ Uploaded By : {UPLOAD_TAG}"
    )


def build_filename(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"


async def progress(current, total, msg: Message):
    percent = current * 100 / total
    filled = int(percent // 10)
    bar = "▰" * filled + "▱" * (10 - filled)
    try:
        await msg.edit(f"📤 Uploading...\n{bar} {percent:.1f}%")
    except:
        pass

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    global THUMB_FILE_ID
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply("✅ Thumbnail saved (persistent)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail not set")

# ================= QUEUE =================
@app.on_message(filters.video | filters.document)
async def add_to_queue(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    QUEUE.append(m)
    await m.reply(f"📥 Added to queue ({len(QUEUE)})")

# ================= START QUEUE =================
@app.on_message(filters.command("start"))
async def start_queue(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    await m.reply(f"🚀 Starting upload of {len(QUEUE)} videos")

    while QUEUE:
        msg = QUEUE.pop(0)
        media = msg.video or msg.document

        anime, season, episode, overall, quality = extract_info(
            media.file_name or "video.mp4"
        )

        status = await msg.reply("📤 Uploading...")

        sent = await client.send_video(
            chat_id=msg.chat.id,
            video=media.file_id,            # FAST reupload
            caption=build_caption(anime, season, episode, overall, quality),
            file_name=build_filename(anime, season, episode, overall, quality),
            thumb=THUMB_FILE_ID,
            supports_streaming=True,
            progress=progress,
            progress_args=(status,)
        )

        LAST_PREVIEW[msg.chat.id] = sent.message_id

    await m.reply("✅ All uploads completed")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m: Message):
    mid = LAST_PREVIEW.get(m.chat.id)
    if not mid:
        return await m.reply("❌ Nothing to preview")
    await app.copy_message(m.chat.id, m.chat.id, mid)

# ================= RUN =================
print("🤖 Anime Qualifier Bot — FINAL STABLE BUILD (PYROGRAM ONLY)")
app.run()
