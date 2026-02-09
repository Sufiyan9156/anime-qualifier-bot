import os, re, time, asyncio
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
CAPTION_PATH = "/tmp/caption.txt"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= APP =================
app = Client(
    "anime_qualifier_runtime",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    workers=1
)

EPISODE_QUEUE = []
RUNNING = False

# ================= UTILS =================
def is_owner(uid): return uid in OWNERS
def pad2(n): return str(n).zfill(2)
def pad3(n): return str(n).zfill(3)

def bar(p):
    return "▰"*(p//10) + "▱"*(10-p//10)

def speed(done, start):
    t = max(1, time.time()-start)
    return f"{done/t/1024/1024:.2f} MB/s"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m):
    if is_owner(m.from_user.id) and m.reply_to_message and m.reply_to_message.photo:
        await app.download_media(m.reply_to_message.photo, THUMB_PATH)
        await m.reply("✅ Thumbnail set")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if is_owner(m.from_user.id) and os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)

@app.on_message(filters.command("del_thumb"))
async def del_thumb(_, m):
    if is_owner(m.from_user.id) and os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
        await m.reply("🗑 Thumbnail deleted")

# ================= CAPTION =================
DEFAULT_CAPTION = (
    "<b>⬡ {anime}</b>\n"
    "<b>╔══════════════════════╗</b>\n"
    "<b>‣ Season : {season}</b>\n"
    "<b>‣ Episode : {ep} ({overall})</b>\n"
    "<b>‣ Audio : Hindi #Official</b>\n"
    "<b>‣ Quality : {quality}</b>\n"
    "<b>╚══════════════════════╝</b>\n"
    "<b>⬡ Uploaded By : {uploader}</b>"
)

def get_caption(**k):
    tpl = DEFAULT_CAPTION
    if os.path.exists(CAPTION_PATH):
        tpl = open(CAPTION_PATH).read()
    return tpl.format(**k)

@app.on_message(filters.command("set_caption"))
async def set_caption(_, m):
    if is_owner(m.from_user.id):
        open(CAPTION_PATH, "w").write(m.text.split(None,1)[1])
        await m.reply("✅ Caption set")

@app.on_message(filters.command("view_caption"))
async def view_caption(_, m):
    if is_owner(m.from_user.id):
        await m.reply(open(CAPTION_PATH).read() if os.path.exists(CAPTION_PATH) else DEFAULT_CAPTION)

@app.on_message(filters.command("del_caption"))
async def del_caption(_, m):
    if is_owner(m.from_user.id) and os.path.exists(CAPTION_PATH):
        os.remove(CAPTION_PATH)
        await m.reply("🗑 Caption reset")

# ================= PARSER =================
def extract_files(text):
    files=[]
    parts=re.split(r"(https://t\.me/\S+)",text)
    for i in range(1,len(parts),2):
        m=re.search(r"-n\s+(.+?\[(480p|720p|1080p|2160p)\])",parts[i+1])
        if m:
            files.append({"link":parts[i],"filename":m.group(1),"quality":m.group(2)})
    return sorted(files,key=lambda x:QUALITY_ORDER.index(x["quality"]))

def parse_multi_episode(text):
    eps=[]
    for b in re.split(r"(?=🎺)",text):
        if not b.startswith("🎺"): continue
        title=re.sub(r"^Episode\s+\d+\s*-\s*","",re.search(r"🎺\s*(.+)",b).group(1))
        overall=int(re.search(r"Episode\s+(\d+)",b).group(1))
        files=extract_files(b)
        if files:
            eps.append({"title":title,"overall":overall,"files":files})
    return sorted(eps,key=lambda x:x["overall"])

# ================= QUEUE =================
@app.on_message((filters.text|filters.caption)&filters.regex("🎺"))
async def queue(_,m):
    if is_owner(m.from_user.id):
        for ep in parse_multi_episode(m.text or m.caption):
            EPISODE_QUEUE.append(ep)
            await m.reply(f"📥 Queued Episode {pad3(ep['overall'])}")

# ================= START =================
@app.on_message(filters.command("start"))
async def start(client,m):
    global RUNNING
    if not is_owner(m.from_user.id) or RUNNING or not EPISODE_QUEUE: return
    RUNNING=True
    try:
        for ep in EPISODE_QUEUE:
            await m.reply(f"<b>🎺 Episode {pad3(ep['overall'])} - {ep['title']}</b>",parse_mode=ParseMode.HTML)
            for it in ep["files"]:
                chat,mid=re.search(r"https://t\.me/([^/]+)/(\d+)",it["link"]).groups()
                src=await client.get_messages(chat,int(mid))
                path=await client.download_media(src)
                await client.send_video(
                    m.chat.id,
                    path,
                    caption=get_caption(
                        anime="Jujutsu Kaisen",
                        season=pad2(1),
                        ep=pad2(int(re.search(r"Episode\s+(\d+)",it["filename"]).group(1))),
                        overall=pad3(ep["overall"]),
                        quality=it["quality"],
                        uploader=UPLOAD_TAG
                    ),
                    thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                    parse_mode=ParseMode.HTML
                )
                os.remove(path)
        await m.reply("✅ Done")
    finally:
        EPISODE_QUEUE.clear()
        RUNNING=False

app.run()
