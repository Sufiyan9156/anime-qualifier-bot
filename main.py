# ===================== Perfect 01 =====================
# Anime Qualifier Bot – Stable Baseline

import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageIdInvalid

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "/tmp/thumb.jpg"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= APP =================
app = Client(
    name="anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

EPISODE_QUEUE = []

# ================= UTILS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS

def progress_bar(pct: int) -> str:
    filled = pct // 10
    return "▰" * filled + "▱" * (10 - filled)

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply photo ke saath /set_thumb")
    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

# ================= FILE PARSER =================
def extract_files(text: str):
    files = []
    for link, name, q in re.findall(
        r"(https://t\.me/\S+)\s+-n\s+(.+?\[(480p|720p|1080p|2160p)\])",
        text
    ):
        files.append({
            "link": link,
            "filename": name,
            "quality": q
        })
    return sorted(files, key=lambda x: QUALITY_ORDER.index(x["quality"]))

# ================= MULTI 🎺 PARSER =================
def parse_multi_episode(text: str):
    episodes = []
    blocks = re.split(r"(?=🎺)", text)

    for block in blocks:
        title_m = re.search(r"🎺\s*(.+)", block)
        overall_m = re.search(r"Episode\s+(\d+)", block)
        files = extract_files(block)

        if not title_m or not overall_m or not files:
            continue

        episodes.append({
            "title": f"<b>🎺 {title_m.group(1)}</b>",
            "overall": int(overall_m.group(1)),
            "files": files
        })

    return sorted(episodes, key=lambda x: x["overall"])

# ================= CAPTION =================
def build_caption(ep_overall, quality):
    return (
        "<b>⬡ Jujutsu Kaisen</b>\n"
        "<b>╔══════════════════════╗</b>\n"
        "<b>‣ Season : 02</b>\n"
        f"<b>‣ Episode : {ep_overall}</b>\n"
        "<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        "<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= QUEUE =================
@app.on_message((filters.text | filters.caption) & filters.regex(r"🎺"))
async def queue_handler(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text or m.caption
    episodes = parse_multi_episode(text)

    if not episodes:
        return await m.reply("❌ Invalid format")

    for ep in episodes:
        EPISODE_QUEUE.append(ep)
        await m.reply(
            f"<b>📥 Queued → Episode {ep['overall']} ({len(ep['files'])} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

# ================= START =================
@app.on_message(filters.command("start"))
async def start_handler(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)

        for item in ep["files"]:
            chat, mid = re.search(
                r"https://t\.me/([^/]+)/(\d+)",
                item["link"]
            ).groups()

            src = await client.get_messages(chat, int(mid))
            status = await m.reply("📥 Downloading...")

            start_time = time.time()
            last_edit = 0

            async def safe_edit(text):
                nonlocal last_edit
                if time.time() - last_edit < 3:
                    return
                last_edit = time.time()
                try:
                    await status.edit(text)
                except (MessageIdInvalid, FloodWait):
                    pass

            def progress_cb(current, total, stage):
                pct = int(current * 100 / total) if total else 0
                bar = progress_bar(pct)
                asyncio.get_event_loop().create_task(
                    safe_edit(f"{stage}\n{bar} {pct}%")
                )

            path = await client.download_media(
                src,
                progress=lambda c, t: progress_cb(c, t, "📥 Downloading")
            )

            while True:
                try:
                    await client.send_video(
                        m.chat.id,
                        path,
                        caption=build_caption(ep["overall"], item["quality"]),
                        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                        supports_streaming=True,
                        parse_mode=ParseMode.HTML,
                        progress=lambda c, t: progress_cb(c, t, "📤 Uploading")
                    )
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)

            try:
                await status.delete()
            except:
                pass

            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("<b>✅ All episodes completed</b>", parse_mode=ParseMode.HTML)

# ================= RUN =================
app.run()
