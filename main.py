import os, re, sys, asyncio, signal, time
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.not_acceptable_406 import AuthKeyDuplicated

# ================= HARD LOCK =================
LOCK_FILE = "/tmp/perfect01.lock"

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        print("AUTH_KEY_DUPLICATED — already running")
        sys.exit(0)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def release_lock(*_):
    try:
        os.remove(LOCK_FILE)
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, release_lock)
signal.signal(signal.SIGTERM, release_lock)
acquire_lock()

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}

LEECH_GC_ID = -1001749401484
LEECH_CMD = "/l1"
KPS_PM_BOT = "KPSLeech1Bot"

UPLOAD_TAG = "@SenpaiAnimess"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= APP =================
app = Client(
    "perfect01_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

# ================= MEMORY =================
EP_QUEUE = []          # episodes to dispatch
WAITING = {}           # episode -> qualities received

# ================= UTILS =================
def is_owner(uid):
    return uid in OWNERS

def extract_files(text):
    out = []
    for link, name, q in re.findall(
        r"(https://t\.me/\S+)\s+-n\s+(.+?\[(480p|720p|1080p|2160p)\])",
        text
    ):
        out.append({
            "link": link,
            "filename": name,
            "quality": q
        })
    return sorted(out, key=lambda x: QUALITY_ORDER.index(x["quality"]))

def parse_blocks(text):
    episodes = []
    blocks = re.split(r"(?=🎺)", text)
    for b in blocks:
        t = re.search(r"🎺\s*(.+)", b)
        o = re.search(r"Episode\s+(\d+)", b)
        f = extract_files(b)
        if t and o and f:
            episodes.append({
                "title": t.group(1),
                "overall": int(o.group(1)),
                "files": f
            })
    return sorted(episodes, key=lambda x: x["overall"])

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex("🎺"))
async def queue_handler(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    eps = parse_blocks(m.text)
    if not eps:
        return await m.reply("❌ Invalid episode format")

    for ep in eps:
        EP_QUEUE.append(ep)
        WAITING[ep["overall"]] = set()

        await m.reply(
            f"<b>📥 Dispatched → Episode {ep['overall']} ({len(ep['files'])} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

        # 🔥 SEND /l1 COMMANDS TO LEECH GC
        for f in ep["files"]:
            cmd = f"{LEECH_CMD} {f['link']} -n {f['filename']}"
            try:
                await app.send_message(LEECH_GC_ID, cmd)
                await asyncio.sleep(2)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)

# ================= KPS PM WATCHER =================
@app.on_message(filters.private & filters.user(KPS_PM_BOT))
async def kps_watcher(_, m: Message):
    text = (m.caption or m.text or "")
    m_ep = re.search(r"Episode\s+\d+\((\d+)\)", text)
    m_q = re.search(r"\[(480p|720p|1080p|2160p)\]", text)

    if not m_ep or not m_q:
        return

    ep = int(m_ep.group(1))
    q = m_q.group(1)

    if ep not in WAITING:
        return

    WAITING[ep].add(q)

    # ✅ ALL 4 QUALITIES RECEIVED
    if len(WAITING[ep]) == 4:
        await app.send_message(
            m.from_user.id,
            (
                f"<b>🎺 Episode {ep} – Completed</b>\n\n"
                f"480p   ✅ Renamed + Captioned + Thumbnail\n"
                f"720p   ✅ Renamed + Captioned + Thumbnail\n"
                f"1080p  ✅ Renamed + Captioned + Thumbnail\n"
                f"2160p  ✅ Renamed + Captioned + Thumbnail"
            ),
            parse_mode=ParseMode.HTML
        )
        del WAITING[ep]

# ================= RUN =================
try:
    app.run()
except AuthKeyDuplicated:
    print("AUTH_KEY_DUPLICATED — session already in use")
finally:
    release_lock()
