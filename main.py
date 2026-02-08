import os, re, time, asyncio, sys, signal
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.not_acceptable_406 import AuthKeyDuplicated

# ================= LOCK (CRITICAL FIX) =================
LOCK_FILE = "/tmp/anime_qualifier.lock"

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        print("❌ Another instance already running. Exiting.")
        sys.exit(0)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def release_lock(*_):
    try:
        os.remove(LOCK_FILE)
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, release_lock)
signal.signal(signal.SIGINT, release_lock)

acquire_lock()

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

def extract_files(text):
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

def parse_multi_episode(text):
    episodes = []
    blocks = re.split(r"(?=🎺)", text)
    for block in blocks:
        t = re.search(r"🎺\s*(.+)", block)
        o = re.search(r"Episode\s+(\d+)", block)
        f = extract_files(block)
        if t and o and f:
            episodes.append({
                "title": f"<b>🎺 {t.group(1)}</b>",
                "overall": int(o.group(1)),
                "files": f
            })
    return sorted(episodes, key=lambda x: x["overall"])

def caption(ep, q):
    return (
        "<b>⬡ Jujutsu Kaisen</b>\n"
        "<b>╔══════════════════════╗</b>\n"
        "<b>‣ Season : 02</b>\n"
        f"<b>‣ Episode : {ep}</b>\n"
        "<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {q}</b>\n"
        "<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply image ke saath /set_thumb")
    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    eps = parse_multi_episode(m.text)
    if not eps:
        return await m.reply("❌ Invalid format")
    for ep in eps:
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

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)

        for f in ep["files"]:
            chat, mid = re.search(r"https://t\.me/([^/]+)/(\d+)", f["link"]).groups()
            msg = await client.get_messages(chat, int(mid))

            path = await client.download_media(msg)

            while True:
                try:
                    await client.send_video(
                        m.chat.id,
                        path,
                        caption=caption(ep["overall"], f["quality"]),
                        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                        supports_streaming=True,
                        parse_mode=ParseMode.HTML
                    )
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)

            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("<b>✅ All episodes done</b>", parse_mode=ParseMode.HTML)

# ================= RUN SAFE =================
try:
    app.run()
except AuthKeyDuplicated:
    print("❌ AUTH_KEY_DUPLICATED — session already running elsewhere")
finally:
    release_lock()
