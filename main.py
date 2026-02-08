import os, re, time, asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

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
        return await m.reply("Reply photo ke saath /set_thumb")

    await app.download_media(
        m.reply_to_message.photo,
        THUMB_PATH,
        force=True
    )
    await m.reply("Thumbnail saved")

# ================= PARSER =================
def extract_files(text):
    files = []
    parts = re.split(r"(https://t\.me/\S+)", text)

    for i in range(1, len(parts), 2):
        link = parts[i]
        tail = parts[i+1] if i+1 < len(parts) else ""

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

    return files

# ================= CAPTION (LOCKED SIMPLE) =================
def caption(anime, season, ep, overall, quality):
    return (
        f"{anime}\n"
        f"----------------------\n"
        f"Season : {season}\n"
        f"Episode : {ep} ({overall})\n"
        f"Audio : Hindi Official\n"
        f"Quality : {quality}\n"
        f"----------------------\n"
        f"Uploaded By : {UPLOAD_TAG}"
    )

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    t = re.search(r"Episode\s+(\d+)", m.text)
    if not t:
        return

    overall = t.group(1)
    files = extract_files(m.text)
    files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

    EPISODE_QUEUE.append(files)
    await m.reply(f"Queued Episode {overall} ({len(files)} qualities)")

# ================= START =================
@app.on_message(filters.command("start"))
async def start(client, m: Message):
    if not is_owner(m.from_user.id):
        return

    for files in EPISODE_QUEUE:
        for item in files:
            chat, mid = re.search(r"https://t\.me/([^/]+)/(\d+)", item["link"]).groups()
            src = await client.get_messages(chat, int(mid))

            prog = await m.reply("Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")
            start = time.time()
            last = 0

            async def upd(stage, c, t):
                p = c * 100 / t if t else 0
                await prog.edit(
                    f"{stage}\n{bar(p)} {int(p)}%\n{speed(c, start)}"
                )

            def cb(c, t, stage):
                nonlocal last
                if time.time() - last < 2:
                    return
                last = time.time()
                client.loop.create_task(upd(stage, c, t))

            path = await client.download_media(
                src,
                progress=lambda c,t: cb(c,t,"Downloading")
            )

            # ⚠️ important delay for thumb
            await asyncio.sleep(2)

            await client.send_video(
                m.chat.id,
                path,
                caption=caption(
                    "Jujutsu Kaisen",
                    "02",
                    "06",
                    "030",
                    item["quality"]
                ),
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                progress=lambda c,t: cb(c,t,"Uploading")
            )

            await prog.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("All qualities uploaded")

app.run()
