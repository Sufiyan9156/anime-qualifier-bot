import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def make_bar(p):
    filled = int(p // 10)
    return "▰" * filled + "▱" * (10 - filled)

def speed_fmt(done, start):
    elapsed = max(1, time.time() - start)
    speed = done / elapsed
    return f"{speed / (1024*1024):.2f} MB/s"

def parse_tme_link(link):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)

async def safe_get_message(client, link):
    chat, mid = parse_tme_link(link)
    try:
        await client.get_chat(chat)
        return await client.get_messages(chat, mid)
    except Exception as e:
        print(f"❌ Source error: {e}")
        return None

# ================= CAPTION =================
def build_caption(filename, quality, overall):
    anime, season, ep = re.search(
        r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)", filename
    ).groups()

    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>‣ Season : {season.zfill(2)}</b>\n"
        f"<b>‣ Episode : {ep.zfill(2)} ({overall})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Reply photo ke saath /set_thumb bhejo")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail set")

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    blocks = re.split(r"(?=🎺)", m.text)
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines or not lines[0].startswith("🎺"):
            continue

        overall = re.search(r"Episode\s+(\d+)", lines[0]).group(1)

        files = []
        for l in lines[1:]:
            m2 = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", l)
            if not m2:
                continue
            name = m2.group(2)
            q = next((x for x in QUALITY_ORDER if x in name), "480p")
            files.append({"link": m2.group(1), "filename": name, "quality": q})

        files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))
        EPISODE_QUEUE.append({"overall": overall, "files": files})

        await m.reply(f"📥 Queued → Episode {overall}", parse_mode=ParseMode.HTML)

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in EPISODE_QUEUE:
        for item in ep["files"]:
            src = await safe_get_message(client, item["link"])
            if not src:
                continue

            progress = await m.reply("📥 Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")

            start = time.time()
            last = 0

            async def dl_progress(cur, total):
                nonlocal last
                if time.time() - last < 2:
                    return
                last = time.time()
                pct = cur * 100 / total if total else 0
                await progress.edit(
                    f"📥 Downloading...\n"
                    f"{make_bar(pct)} {int(pct)}%\n"
                    f"⏩ {speed_fmt(cur, start)}"
                )

            path = await client.download_media(src, progress=dl_progress)

            start = time.time()
            last = 0

            async def ul_progress(cur, total):
                nonlocal last
                if time.time() - last < 2:
                    return
                last = time.time()
                pct = cur * 100 / total if total else 0
                await progress.edit(
                    f"📤 Uploading...\n"
                    f"{make_bar(pct)} {int(pct)}%\n"
                    f"⏩ {speed_fmt(cur, start)}"
                )

            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(
                    item["filename"],
                    item["quality"],
                    ep["overall"]
                ),
                file_name=item["filename"],
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=False,
                progress=ul_progress,
                parse_mode=ParseMode.HTML
            )

            await progress.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("<b>✅ All episodes completed</b>", parse_mode=ParseMode.HTML)

print("🤖 Anime Qualifier — FINAL REAL SPEED BUILD")
app.run()
