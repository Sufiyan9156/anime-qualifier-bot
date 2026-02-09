import os, re, time, asyncio
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

app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []

# ================= UTILS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS

def bar(p):
    f = int(p // 10)
    return "▰" * f + "▱" * (10 - f)

def speed(done, start):
    t = max(1, time.time() - start)
    return f"{done / t / (1024 * 1024):.2f} MB/s"

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
    parts = re.split(r"(https://t\.me/\S+)", text)

    for i in range(1, len(parts), 2):
        link = parts[i]
        tail = parts[i + 1] if i + 1 < len(parts) else ""

        m = re.search(
            r"-n\s+(.+?\[(480p|720p|1080p|2160p)\])",
            tail
        )
        if not m:
            continue

        files.append({
            "link": link,
            "filename": m.group(1),
            "quality": m.group(2)
        })

    return sorted(files, key=lambda x: QUALITY_ORDER.index(x["quality"]))

# ================= MULTI 🎺 PARSER =================
def parse_multi_episode(text: str):
    episodes = []
    blocks = re.split(r"(?=🎺)", text)

    for block in blocks:
        block = block.strip()
        if not block.startswith("🎺"):
            continue

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
def build_caption(anime, season, ep, overall, quality):
    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>╔══════════════════════╗</b>\n"
        f"<b>‣ Season : {season}</b>\n"
        f"<b>‣ Episode : {ep} ({overall})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= QUEUE (TEXT + CAPTION SAFE) =================
@app.on_message((filters.text | filters.caption) & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text or m.caption
    episodes = parse_multi_episode(text)

    if not episodes:
        return await m.reply("❌ No valid episodes found")

    for ep in episodes:
        EPISODE_QUEUE.append(ep)
        await m.reply(
            f"<b>📥 Queued → Episode {ep['overall']} ({len(ep['files'])} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

# ================= START =================
@app.on_message(filters.command("start"))
async def start(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    EPISODE_QUEUE.sort(key=lambda x: x["overall"])

for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)

        for item in ep["files"]:
            chat, mid = re.search(
                r"https://t\.me/([^/]+)/(\d+)",
                item["link"]
            ).groups()

            src = await client.get_messages(chat, int(mid))
            prog = await m.reply("📥 Downloading...")
            start_t = time.time()
            last_edit = 0

            async def safe_edit(text):
                nonlocal last_edit
                if time.time() - last_edit < 3:
                    return
                last_edit = time.time()
                try:
                    await prog.edit(text)
                except (MessageIdInvalid, FloodWait):
                    pass

            def cb(c, t, stage):
                pct = int(c * 100 / t) if t else 0
                client.loop.create_task(
                    safe_edit(f"{stage}\n{bar(pct)} {pct}%\n{speed(c, start_t)}")
                )

            path = await client.download_media(
                src,
                progress=lambda c, t: cb(c, t, "📥 Downloading")
            )

            await asyncio.sleep(3)

            while True:
                try:
                    await client.send_video(
                        m.chat.id,
                        path,
                        caption=build_caption(
                            "Jujutsu Kaisen",
                            "02",
                            re.search(r"Episode\s+(\d+)", item["filename"]).group(1),
                            ep["overall"],
                            item["quality"]
                        ),
                        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                        supports_streaming=True,
                        parse_mode=ParseMode.HTML,
                        progress=lambda c, t: cb(c, t, "📤 Uploading")
                    )
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)

            try:
                await prog.delete()
            except:
                pass

            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply(
        "<b>✅ All episodes & qualities uploaded successfully</b>",
        parse_mode=ParseMode.HTML
    )

app.run()
