import os, re, asyncio, time, sys, signal
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.not_acceptable_406 import AuthKeyDuplicated

# ================== HARD LOCK ==================
LOCK = "/tmp/aq.lock"

def lock():
    if os.path.exists(LOCK):
        print("Already running, exit.")
        sys.exit(0)
    open(LOCK, "w").write(str(os.getpid()))

def unlock(*_):
    try: os.remove(LOCK)
    except: pass
    sys.exit(0)

signal.signal(signal.SIGINT, unlock)
signal.signal(signal.SIGTERM, unlock)
lock()

# ================== ENV ==================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================== CONFIG ==================
OWNERS = {709844068, 6593273878}
LEECH_BOT = "KPSLeech1Bot"
UPLOAD_TAG = "@SenpaiAnimess"
THUMB = "/tmp/thumb.jpg"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================== APP ==================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

QUEUE = []

# ================== UTILS ==================
def owner(uid): return uid in OWNERS

def parse_blocks(text):
    eps = []
    blocks = re.split(r"(?=🎺)", text)
    for b in blocks:
        t = re.search(r"🎺\s*(.+)", b)
        o = re.search(r"Episode\s+(\d+)", b)
        files = re.findall(
            r"(https://t\.me/\S+)\s+-n\s+(.+?\[(480p|720p|1080p|2160p)\])",
            b
        )
        if not (t and o and files): continue
        eps.append({
            "title": t.group(1),
            "overall": int(o.group(1)),
            "files": sorted(
                [{"link": l, "name": n, "q": q} for l,n,q in files],
                key=lambda x: QUALITY_ORDER.index(x["q"])
            )
        })
    return sorted(eps, key=lambda x: x["overall"])

def summary(ep):
    lines = [f"<b>🎺 {ep['title']}</b>"]
    for f in ep["files"]:
        lines.append(f"{f['q']} (Renamed + Caption + Thumb ✅)")
    return "\n".join(lines)

# ================== THUMB ==================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not owner(m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply image ke saath /set_thumb")
    await app.download_media(m.reply_to_message.photo, THUMB)
    await m.reply("✅ Thumbnail saved")

# ================== QUEUE ==================
@app.on_message(filters.text & filters.regex("🎺"))
async def queue(_, m: Message):
    if not owner(m.from_user.id): return
    eps = parse_blocks(m.text)
    if not eps:
        return await m.reply("❌ Format invalid")
    for e in eps:
        QUEUE.append(e)
        await m.reply(
            f"<b>📥 Queued → Episode {e['overall']} ({len(e['files'])} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

# ================== START ==================
@app.on_message(filters.command("start"))
async def start(client, m: Message):
    if not owner(m.from_user.id): return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    for ep in QUEUE:
        # 1️⃣ SEND TASKS TO LEECH BOT PM
        for f in ep["files"]:
            cmd = f"/l1 {f['link']} -n {f['name']} {UPLOAD_TAG}"
            await client.send_message(LEECH_BOT, cmd)
            await asyncio.sleep(2)  # human-like

        # 2️⃣ SUMMARY BACK TO QUALIFIER PM
        await m.reply(summary(ep), parse_mode=ParseMode.HTML)

    QUEUE.clear()
    await m.reply("<b>✅ All episodes dispatched successfully</b>", parse_mode=ParseMode.HTML)

# ================== RUN ==================
try:
    app.run()
except AuthKeyDuplicated:
    print("AUTH_KEY_DUPLICATED – same session elsewhere")
finally:
    unlock()
