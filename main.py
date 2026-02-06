import os
import re
import asyncio
import time
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"

QUALITY_ORDER = {
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "2160p": 4
}

# ================= USER CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================= STORAGE =================
# episodes[episode_no] = {
#   "title": str,
#   "files": {quality: filename}
# }
EPISODES = defaultdict(lambda: {
    "title": "",
    "files": {}
})

CURRENT_EP = None

# ================= HELPERS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS


def extract_episode_header(text: str):
    """
    🎺 Episode 025 - Hidden Inventory
    """
    m = re.search(r"Episode\s+(\d+)\s*-\s*(.+)", text, re.I)
    if not m:
        return None, None
    return int(m.group(1)), m.group(2).strip()


def extract_filename(text: str):
    """
    -n Jujutsu Kaisen Season 02 Episode 01(001) [720p] @SenpaiAnimess
    """
    m = re.search(r"-n\s+(.+)", text)
    return m.group(1).strip() if m else None


def detect_quality(name: str):
    n = name.lower()
    if "2160" in n or "4k" in n:
        return "2160p"
    if "1080" in n:
        return "1080p"
    if "720" in n:
        return "720p"
    return "480p"


# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message.photo:
        return await m.reply("❌ Reply with PHOTO only")

    try:
        if os.path.exists(THUMB_PATH):
            os.remove(THUMB_PATH)

        await client.download_media(m.reply_to_message.photo, THUMB_PATH)
        await m.reply("✅ Thumbnail saved")
    except:
        await m.reply("❌ Thumbnail failed")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("❌ Thumbnail not set")


@app.on_message(filters.command("delete_thumb"))
async def delete_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
        await m.reply("🗑 Thumbnail deleted")
    else:
        await m.reply("❌ Thumbnail not set")

# ================= INPUT HANDLER =================
@app.on_message(filters.text & ~filters.command)
async def collect(_, m: Message):
    global CURRENT_EP

    if not is_owner(m.from_user.id):
        return

    text = m.text.strip()

    # Episode header
    ep_no, title = extract_episode_header(text)
    if ep_no:
        CURRENT_EP = ep_no
        EPISODES[ep_no]["title"] = title
        return

    # File line
    if CURRENT_EP and "-n" in text:
        filename = extract_filename(text)
        if not filename:
            return

        q = detect_quality(filename)
        EPISODES[CURRENT_EP]["files"][q] = filename


# ================= START =================
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not EPISODES:
        return await m.reply("❌ No episodes found")

    for ep_no in sorted(EPISODES):
        data = EPISODES[ep_no]

        lines = [
            f"🎺 Episode {ep_no:03d} - {data['title']}",
            ""
        ]

        for q in sorted(data["files"], key=lambda x: QUALITY_ORDER[x]):
            lines.append(data["files"][q])

        await m.reply("\n".join(lines))
        await asyncio.sleep(1)

    EPISODES.clear()
    await m.reply("✅ Done")

# ================= RUN =================
print("🤖 Anime Qualifier — FINAL STABLE BUILD")
app.run()
