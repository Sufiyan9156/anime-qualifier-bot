import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageIdInvalid, AuthKeyDuplicated

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
    name="anime_qualifier_runtime",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,          # 🔥 prevents session file duplication
    workers=1                # 🔥 avoids parallel auth crash
)

EPISODE_QUEUE = []
RUNNING = False

# ================= UTILS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS

def pad2(n: int) -> str:
    return str(n).zfill(2)

def pad3(n: int) -> str:
    return str(n).zfill(3)

def bar(p: int) -> str:
    f = p // 10
    return "▰" * f + "▱" * (10 - f)

def speed(done: int, start: float) -> str:
    t = max(1, time.time() - start)
    return f"{done / t / (1024*1024):.2f} MB/s"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Photo reply karke /set_thumb bhejo")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail set")

# ================= FILE PARSER =================
def extract_files(text: str):
    files = []
    parts = re.split(r"(https://t\.me/\S+)", text)

    for i in range(1, len(parts), 2):
        link = parts[i]
        tail = parts[i+1] if i+1 < len(parts) else ""

        m = re.search(r"-n\s+(.+?\[(480p|720p|1080p|2160p)\])", tail)
        if not m:
            continue

        files.append({
            "link": link,
            "filename": m.group(1),
            "quality": m.group(2)
        })

    return sorted(files, key=lambda x: QUALITY_ORDER.index(x["quality"]))

# ================= MULTI EP PARSER =================
def parse_multi_episode(text: str):
    eps = []
    blocks = re.split(r"(?=🎺)", text)

    for b in blocks:
        b = b.strip()
        if not b.startswith("🎺"):
            continue

        title_m = re.search(r"🎺\s*(.+)", b)
        overall_m = re.search(r"Episode\s+(\d+)", b)
        files = extract_files(b)

        if not title_m or not overall_m or not files:
            continue

        raw_title = title_m.group(1)

        # 🔥 FIX: remove "Episode 001 - " from title
        clean_title = re.sub(r"^Episode\s+\d+\s*-\s*", "", raw_title).strip()

        eps.append({
            "title": clean_title,              # ✅ only "Ryomen Sukuna"
            "overall": int(overall_m.group(1)),
            "files": files
        })

    return sorted(eps, key=lambda x: x["overall"])

# ================= CAPTION =================
def build_caption(anime, season, ep, overall, quality):
    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>╔══════════════════════╗</b>\n"
        f"<b>‣ Season : {pad2(season)}</b>\n"
        f"<b>‣ Episode : {pad2(ep)} ({pad3(overall)})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= QUEUE =================
@app.on_message((filters.text | filters.caption) & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text or m.caption
    eps = parse_multi_episode(text)

    if not eps:
        return await m.reply("❌ Valid episode data nahi mila")

    for ep in eps:
        EPISODE_QUEUE.append(ep)
        await m.reply(
            f"📥 Queued → Episode {pad3(ep['overall'])} ({len(ep['files'])} qualities)",
            parse_mode=ParseMode.HTML
        )

# ================= START =================
@app.on_message(filters.command("start"))
async def start(client: Client, m: Message):
    global RUNNING
    if not is_owner(m.from_user.id):
        return

    if RUNNING:
        return await m.reply("⚠️ Already running")

    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    RUNNING = True
    EPISODE_QUEUE.sort(key=lambda x: x["overall"])

    try:
        for ep in EPISODE_QUEUE:
            await m.reply(f"<b>🎺 Episode {pad3(ep['overall'])} - {ep['title']}</b>", parse_mode=ParseMode.HTML)

            for item in ep["files"]:
                chat, mid = re.search(r"https://t\.me/([^/]+)/(\d+)", item["link"]).groups()
                src = await client.get_messages(chat, int(mid))

                prog = await m.reply("📥 Downloading...")
                start_t = time.time()
                last = 0

                async def safe_edit(txt):
                    nonlocal last
                    if time.time() - last < 3:
                        return
                    last = time.time()
                    try:
                        await prog.edit(txt)
                    except:
                        pass

                def cb(c, t, stage):
                    pct = int(c*100/t) if t else 0
                    client.loop.create_task(
                        safe_edit(f"{stage}\n{bar(pct)} {pct}%\n{speed(c,start_t)}")
                    )

                path = await client.download_media(src, progress=lambda c,t: cb(c,t,"📥 Downloading"))
                await asyncio.sleep(2)

                await client.send_video(
                    m.chat.id,
                    path,
                    caption=build_caption(
                        "Jujutsu Kaisen",
                        1,
                        int(re.search(r"Episode\s+(\d+)", item["filename"]).group(1)),
                        ep["overall"],
                        item["quality"]
                    ),
                    thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                    supports_streaming=True,
                    parse_mode=ParseMode.HTML,
                    progress=lambda c,t: cb(c,t,"📤 Uploading")
                )

                await prog.delete()
                os.remove(path)

        await m.reply("✅ All episodes uploaded successfully")

    except AuthKeyDuplicated:
        await m.reply("❌ SESSION DUPLICATED\n\nSame account kahin aur login hai.\nMobile / other server logout karo.")
    finally:
        EPISODE_QUEUE.clear()
        RUNNING = False

# ================= RUN =================
app.run()
