# ===================== PERFECT 01 =====================
# Leech Orchestrator + Collector + Final Uploader
# =====================================================

import os, re, time, asyncio
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}

LEECH_BOT = "KPSLeech1Bot"          # only l1
LEECH_CMD = "/l1"

UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "/tmp/thumb.jpg"

ANIME = "Jujutsu Kaisen"
SEASON = "02"

QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================= STATE =================
TASK_QUEUE = []   # parsed episode tasks
COLLECTOR = defaultdict(dict)  
# COLLECTOR[episode][quality] = message

# ================= UTILS =================
def is_owner(uid): 
    return uid in OWNERS

def bar(p):
    f = int(p // 10)
    return "▰" * f + "▱" * (10 - f)

def speed(done, start):
    t = max(1, time.time() - start)
    return f"{done / t / (1024*1024):.2f} MB/s"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Reply photo ke saath /set_thumb")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

# ================= PARSER =================
def parse_bulk(text: str):
    episodes = []
    blocks = re.split(r"(?=🎺)", text)

    for block in blocks:
        block = block.strip()
        if not block.startswith("🎺"):
            continue

        title = re.search(r"🎺\s*(.+)", block)
        overall = re.search(r"Episode\s+(\d+)", block)

        if not title or not overall:
            continue

        files = []
        parts = re.split(r"(https://t\.me/\S+)", block)

        for i in range(1, len(parts), 2):
            link = parts[i]
            tail = parts[i + 1] if i + 1 < len(parts) else ""
            m = re.search(r"-n\s+(.+?\[(480p|720p|1080p|2160p)\])", tail)
            if not m:
                continue
            files.append({
                "link": link,
                "filename": m.group(1),
                "quality": m.group(2)
            })

        files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))
        if files:
            episodes.append({
                "title": title.group(1),
                "overall": int(overall.group(1)),
                "files": files
            })

    return sorted(episodes, key=lambda x: x["overall"])

# ================= CAPTION =================
def build_caption(ep_no, quality):
    return (
        f"<b>⬡ {ANIME}</b>\n"
        f"<b>╔══════════════════════╗</b>\n"
        f"<b>‣ Season : {SEASON}</b>\n"
        f"<b>‣ Episode : {str(ep_no).zfill(2)} ({ep_no})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= QUEUE INPUT =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    eps = parse_bulk(m.text)
    if not eps:
        return await m.reply("❌ No valid episodes found")

    for ep in eps:
        TASK_QUEUE.append(ep)
        await m.reply(
            f"<b>📥 Queued → Episode {ep['overall']} ({len(ep['files'])} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

# ================= SEND TO LEECH BOT =================
async def send_to_leech(ep):
    for item in ep["files"]:
        cmd = f"{LEECH_CMD} {item['link']} -n {item['filename']}"
        await app.send_message(LEECH_BOT, cmd)
        await asyncio.sleep(2)

# ================= COLLECT FROM LEECH BOT =================
@app.on_message(filters.private & filters.video)
async def collect(_, m: Message):
    if m.from_user.username != LEECH_BOT:
        return

    name = m.video.file_name or ""
    q = next((x for x in QUALITY_ORDER if x in name), None)
    ep = re.search(r"\((\d+)\)", name)

    if not q or not ep:
        return

    ep_no = int(ep.group(1))
    COLLECTOR[ep_no][q] = m

    # when all 4 qualities collected
    if len(COLLECTOR[ep_no]) == 4:
        await finalize_episode(ep_no)

# ================= FINAL UPLOAD =================
async def finalize_episode(ep_no):
    await app.send_message(
        "me",
        f"<b>🎺 Episode {ep_no}</b>",
        parse_mode=ParseMode.HTML
    )

    for q in QUALITY_ORDER:
        msg = COLLECTOR[ep_no][q]

        start = time.time()
        prog = await app.send_message("me", f"📤 Uploading {q}...")

        async def cb(c, t):
            p = int(c * 100 / t) if t else 0
            await prog.edit(
                f"📤 Uploading {q}\n{bar(p)} {p}%\n{speed(c, start)}"
            )

        path = await msg.download(progress=cb)

        while True:
            try:
                await app.send_video(
                    "me",
                    path,
                    caption=build_caption(ep_no, q),
                    thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                    parse_mode=ParseMode.HTML
                )
                break
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)

        os.remove(path)
        await prog.delete()

    await app.send_message(
        "me",
        f"<b>🎺 Episode {ep_no} completed</b>\n"
        f"480p ✓\n720p ✓\n1080p ✓\n2160p ✓",
        parse_mode=ParseMode.HTML
    )

    del COLLECTOR[ep_no]

# ================= START PROCESS =================
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not TASK_QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in TASK_QUEUE:
        await send_to_leech(ep)

    TASK_QUEUE.clear()
    await m.reply("✅ All leech tasks sent. Waiting for files...")

# =====================================================
print("🤖 PERFECT 01 — Leech Orchestrator Running")
app.run()
