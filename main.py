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
QUEUE = []          # list of Message objects

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

    if "2160" in up or "4K" in up:
        quality = "2k"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"
    else:
        quality = "480p"

    s, e = "01", "01"
    m = re.search(r"S(\d{1,2})\s*E(\d{1,3})", up)
    if m:
        s, e = m.group(1), m.group(2)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{int(e):03d}"

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
    bar = "▰" * int(percent // 10) + "▱" * (10 - int(percent // 10))
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
        return await m.reply("❌ Photo reply karo")

    THUMB_FILE_ID = m.reply_to_message.photo.file_id
    await m.reply("✅ Thumbnail saved (persistent)")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if THUMB_FILE_ID:
        await m.reply_photo(THUMB_FILE_ID, caption="🖼 Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail not set")

# ================= ADD TO QUEUE =================
@app.on_message(filters.video | filters.document)
async def add_to_queue(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    QUEUE.append(m)
    await m.reply(f"📥 Added to queue ({len(QUEUE)})")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m: Message):
    if not QUEUE:
        return await m.reply("❌ Nothing to preview")

    msg = QUEUE[-1]
    media = msg.video or msg.document

    a, s, e, o, q = extract_info(media.file_name or "video.mp4")

    await m.reply(
        f"🧪 **Preview (Not Uploaded)**\n\n"
        f"📄 Filename:\n`{build_filename(a, s, e, o, q)}`\n\n"
        f"{build_caption(a, s, e, o, q)}"
    )

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    await m.reply(f"🚀 Uploading {len(QUEUE)} videos")

    while QUEUE:
        msg = QUEUE.pop(0)
        media = msg.video or msg.document

        a, s, e, o, q = extract_info(media.file_name or "video.mp4")

        status = await msg.reply("📤 Uploading...")

        await client.send_video(
            chat_id=msg.chat.id,
            video=media.file_id,
            caption=build_caption(a, s, e, o, q),
            file_name=build_filename(a, s, e, o, q),
            thumb=THUMB_FILE_ID,
            supports_streaming=True,
            progress=progress,
            progress_args=(status,)
        )

        await status.delete()

    await m.reply("✅ All uploads completed")

# ================= RUN =================
print("🤖 Anime Qualifier Bot — STABLE FINAL BUILD")
app.run()
