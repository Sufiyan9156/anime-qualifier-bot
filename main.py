import os, re, time, asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

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

def make_bar(p):
    f = int(p // 10)
    return "▰" * f + "▱" * (10 - f)

def speed_fmt(done, start):
    elapsed = max(1, time.time() - start)
    return f"{done / elapsed / (1024*1024):.2f} MB/s"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Reply photo ke saath /set_thumb")

    await app.download_media(
        m.reply_to_message.photo,
        THUMB_PATH,
        force=True
    )
    await m.reply("✅ Thumbnail set")

# ================= PARSER =================
def extract_files(text):
    files = []
    parts = re.split(r"(https://t\.me/\S+)", text)

    for i in range(1, len(parts), 2):
        link = parts[i]
        tail = parts[i+1] if i+1 < len(parts) else ""

        m = re.search(
            r"-n\s+(.+?\[(480p|720p|1080p|2160p)\][^@\n]*)",
            tail
        )
        if not m:
            continue

        files.append({
            "link": link,
            "filename": m.group(1).strip(),
            "quality": m.group(2)
        })

    return files

# ================= CAPTION (LOCKED) =================
def build_caption(filename, quality, overall):
    anime, season, ep = re.search(
        r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)",
        filename
    ).groups()

    return (
        f"⬡ {anime}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"‣ Season : {season.zfill(2)}\n"
        f"‣ Episode : {ep.zfill(2)} ({overall})\n"
        f"‣ Audio : Hindi #Official\n"
        f"‣ Quality : {quality}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⬡ Uploaded By : {UPLOAD_TAG}"
    )

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    t = re.search(r"🎺\s*(Episode\s+\d+\s+–\s+.+)", m.text)
    if not t:
        return

    overall = re.search(r"Episode\s+(\d+)", t.group(1)).group(1)
    files = extract_files(m.text)
    files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

    EPISODE_QUEUE.append({
        "title": f"🎺 {t.group(1)}",
        "overall": overall,
        "files": files
    })

    await m.reply(
        f"📥 Queued → Episode {overall} ({len(files)} qualities)"
    )

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"])

        for item in ep["files"]:
            chat, mid = re.search(
                r"https://t\.me/([^/]+)/(\d+)",
                item["link"]
            ).groups()

            src = await client.get_messages(chat, int(mid))

            prog = await m.reply("📥 Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")
            start = time.time()
            last = 0

            async def update(stage, cur, total):
                pct = cur * 100 / total if total else 0
                await prog.edit(
                    f"{stage}\n"
                    f"{make_bar(pct)} {int(pct)}%\n"
                    f"⏩ {speed_fmt(cur, start)}"
                )

            def progress_cb(cur, total, stage):
                nonlocal last
                if time.time() - last < 2:
                    return
                last = time.time()
                client.loop.create_task(update(stage, cur, total))

            path = await client.download_media(
                src,
                progress=lambda c,t: progress_cb(c,t,"📥 Downloading")
            )

            start = time.time()
            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(
                    item["filename"],
                    item["quality"],
                    ep["overall"]
                ),
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=False,
                progress=lambda c,t: progress_cb(c,t,"📤 Uploading"),
                parse_mode=ParseMode.DEFAULT
            )

            await prog.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("✅ All qualities uploaded")

print("🤖 Anime Qualifier — FINAL LOCKED BUILD")
app.run()
