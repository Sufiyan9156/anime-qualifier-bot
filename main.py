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
    session_string=SESSION_STRING,
    in_memory=True
)

EPISODE_QUEUE = []

# ================= UTILS =================
def is_owner(uid): 
    return uid in OWNERS

def bar(p):
    f = p // 10
    return "▰"*f + "▱"*(10-f)

def speed(done, start):
    t = max(1, time.time() - start)
    return f"{done/t/(1024*1024):.2f} MB/s"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply photo ke saath /set_thumb")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

# ================= PARSER =================
def extract_files(text):
    files = []
    parts = re.split(r"(https://t\.me/\S+)", text)

    for i in range(1, len(parts), 2):
        link = parts[i]
        tail = parts[i+1] if i+1 < len(parts) else ""
        m = re.search(r"-n\s+(.+?\[(480p|720p|1080p|2160p)\])", tail)
        if m:
            files.append({
                "link": link,
                "filename": m.group(1),
                "quality": m.group(2)
            })

    return sorted(files, key=lambda x: QUALITY_ORDER.index(x["quality"]))

def parse_multi_episode(text):
    eps = []
    blocks = re.split(r"(?=🎺)", text)

    for b in blocks:
        if not b.startswith("🎺"):
            continue

        title = re.search(r"🎺\s*(.+)", b)
        num = re.search(r"Episode\s+(\d+)", b)
        files = extract_files(b)

        if title and num and files:
            eps.append({
                "title": title.group(1),
                "num": int(num.group(1)),
                "files": files
            })

    return sorted(eps, key=lambda x: x["num"])

# ================= CAPTION =================
def caption(ep_no, quality):
    ep2 = f"{ep_no:02d}"
    ep3 = f"{ep_no:03d}"
    return (
        "<b>⬡ Jujutsu Kaisen</b>\n"
        "<b>╔══════════════════════╗</b>\n"
        "<b>‣ Season : 01</b>\n"
        f"<b>‣ Episode : {ep2} ({ep3})</b>\n"
        "<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        "<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= QUEUE =================
@app.on_message((filters.text | filters.caption) & filters.regex("🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    eps = parse_multi_episode(m.text or m.caption)
    if not eps:
        return await m.reply("❌ Invalid format")

    EPISODE_QUEUE.extend(eps)
    await m.reply(f"📥 Queued {len(eps)} episode(s)")

# ================= START =================
@app.on_message(filters.command("start"))
async def start(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not EPISODE_QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in EPISODE_QUEUE:
        ep3 = f"{ep['num']:03d}"
        await m.reply(f"<b>🎺 Episode {ep3} – {ep['title']}</b>", parse_mode=ParseMode.HTML)

        for item in ep["files"]:
            chat, mid = re.search(r"https://t\.me/([^/]+)/(\d+)", item["link"]).groups()
            src = await client.get_messages(chat, int(mid))

            prog = await m.reply("📥 Downloading…")
            start_t = time.time()
            last = 0

            async def safe_edit(t):
                nonlocal last
                if time.time() - last > 3:
                    last = time.time()
                    try: await prog.edit(t)
                    except: pass

            def cb(c, t, s):
                pct = int(c*100/t) if t else 0
                client.loop.create_task(
                    safe_edit(f"{s}\n{bar(pct)} {pct}%\n{speed(c,start_t)}")
                )

            path = await client.download_media(src, progress=lambda c,t: cb(c,t,"📥 Downloading"))

            while True:
                try:
                    await client.send_video(
                        m.chat.id,
                        path,
                        caption=caption(ep["num"], item["quality"]),
                        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                        supports_streaming=True,
                        parse_mode=ParseMode.HTML,
                        progress=lambda c,t: cb(c,t,"📤 Uploading")
                    )
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value+1)

            await prog.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("<b>✅ Done</b>", parse_mode=ParseMode.HTML)

app.run()
