import os
import re
import asyncio
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "thumb.jpg"

# ================= GLOBALS =================
QUEUE = []

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= ANI LIST =================
ANILIST_URL = "https://graphql.anilist.co"

def anilist_search(title: str) -> str:
    query = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        title {
          english
          romaji
        }
      }
    }
    """
    variables = {"search": title}
    try:
        r = requests.post(ANILIST_URL, json={"query": query, "variables": variables}, timeout=10)
        data = r.json()["data"]["Media"]["title"]
        return data["english"] or data["romaji"]
    except:
        return title.title()

# ================= HELPERS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS


def extract_basic(filename: str):
    name = filename.lower()

    # QUALITY
    if "2160" in name or "4k" in name:
        q = "2K"
    elif "1080" in name:
        q = "1080p"
    elif "720" in name:
        q = "720p"
    else:
        q = "480p"

    # SEASON / EP
    s, e = 1, 1
    m = re.search(r"s(\d{1,2})\D*e(\d{1,3})", name)
    if m:
        s, e = int(m.group(1)), int(m.group(2))

    # CLEAN TITLE GUESS
    clean = re.sub(
        r"\[.*?\]|s\d+e\d+|\d{3,4}p|4k|hindi|dual|web|hdrip|bluray|x264|x265|aac|mp4|mkv|@\w+",
        "",
        name
    )
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean.title(), f"{s:02d}", f"{e:02d}", f"{e:03d}", q


def build_filename(anime, s, e, o, q):
    return f"{anime} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"


def build_caption(anime, s, e, o, q):
    return (
        f"⬡ **{anime}**\n"
        f"╭━━━━━━━━━━━━━━━━━━\n"
        f"‣ Season : {s}\n"
        f"‣ Episode : {e}({o})\n"
        f"‣ Audio : Hindi #Official\n"
        f"‣ Quality : {q}\n"
        f"╰━━━━━━━━━━━━━━━━━━\n"
        f"⬡ Uploaded By : {UPLOAD_TAG}"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved")


# ================= ADD TO QUEUE =================
@app.on_message(filters.video | filters.document)
async def add_queue(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    base_title, s, e, o, q = extract_basic(media.file_name or "video.mp4")

    final_anime = anilist_search(base_title)

    QUEUE.append({
        "file_id": media.file_id,
        "filename": build_filename(final_anime, s, e, o, q),
        "caption": build_caption(final_anime, s, e, o, q)
    })

    await m.reply(f"📥 Added to queue ({len(QUEUE)})")


# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m: Message):
    if not QUEUE:
        return await m.reply("❌ Nothing to preview")

    item = QUEUE[-1]
    await m.reply(
        f"🧪 **PREVIEW (Not Uploaded)**\n\n"
        f"**Filename:**\n{item['filename']}\n\n"
        f"{item['caption']}"
    )


# ================= START UPLOAD =================
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
            caption=item["caption"],
            file_name=item["filename"],
            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
            supports_streaming=True
        )

        os.remove(path)
        await asyncio.sleep(1)

    await m.reply("✅ All uploads done")

# ================= RUN =================
print("🤖 Anime Qualifier Bot — FINAL ANI LIST BUILD LIVE")
app.run()
