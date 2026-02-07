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

async def fake_progress(msg, text, seconds=8):
    for i in range(1, 11):
        await msg.edit(
            f"{text}\n{make_bar(i*10)} {i*10}%"
        )
        await asyncio.sleep(seconds / 10)

def parse_tme_link(link):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)

async def safe_get_message(client, link):
    chat, mid = parse_tme_link(link)
    try:
        await client.get_chat(chat)   # peer resolve fix
        return await client.get_messages(chat, mid)
    except Exception as e:
        print(f"❌ Source error: {e}")
        return None

# ================= TITLE =================
def format_title(raw):
    m = re.match(r"🎺\s*(Episode\s+\d+)\s+–\s+(.+)", raw)
    if not m:
        return f"<b>{raw}</b>"
    ep, name = m.groups()
    return f"<b>🎺 {ep} – {name}</b>"

# ================= PARSER =================
def parse_multi_episode(text):
    blocks = re.split(r"(?=🎺)", text)
    episodes = []

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines or not lines[0].startswith("🎺"):
            continue

        raw_title = lines[0]
        title = format_title(raw_title)
        overall = re.search(r"Episode\s+(\d+)", raw_title).group(1)

        files = []
        for l in lines[1:]:
            m = re.search(r"(https://t\.me/\S+)\s+-n\s+(.+)", l)
            if not m:
                continue

            name = m.group(2)
            q = next((x for x in QUALITY_ORDER if x in name), "480p")
            files.append({
                "link": m.group(1),
                "filename": name,
                "quality": q
            })

        files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))
        episodes.append({"title": title, "overall": overall, "files": files})

    return episodes

# ================= CAPTION =================
def build_caption(filename, quality, overall):
    anime, season, ep = re.search(
        r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)", filename
    ).groups()

    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>╔══════════════════════╗</b>\n"
        f"<b>‣ Season : {season.zfill(2)}</b>\n"
        f"<b>‣ Episode : {ep.zfill(2)} ({overall})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>╚══════════════════════╝</b>\n"
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

    for ep in parse_multi_episode(m.text):
        EPISODE_QUEUE.append(ep)
        await m.reply(f"📥 Queued → {ep['title']}", parse_mode=ParseMode.HTML)

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)

        for item in ep["files"]:
            src = await safe_get_message(client, item["link"])
            if not src:
                continue

            progress_msg = await m.reply("📥 Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")

            dl_task = asyncio.create_task(
                fake_progress(progress_msg, "📥 Downloading...")
            )

            path = await client.download_media(src)
            dl_task.cancel()

            ul_task = asyncio.create_task(
                fake_progress(progress_msg, "📤 Uploading...")
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
                supports_streaming=False,  # 🔥 EXACT FILE SIZE
                parse_mode=ParseMode.HTML
            )

            ul_task.cancel()
            await progress_msg.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("<b>✅ All episodes completed</b>", parse_mode=ParseMode.HTML)

print("🤖 Anime Qualifier — FINAL STABLE PRODUCTION BUILD")
app.run()
