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

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

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

# ================= CAPTION (BOLD – EXACT FORMAT) =================
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

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    title = re.search(r"🎺\s*(.+)", m.text)
    overall = re.search(r"Episode\s+(\d+)", m.text)

    if not title or not overall:
        return

    files = extract_files(m.text)
    files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

    EPISODE_QUEUE.append({
        "title": f"<b>🎺 {title.group(1)}</b>",
        "overall": overall.group(1),
        "files": files
    })

    await m.reply(
        f"<b>📥 Queued → Episode {overall.group(1)} ({len(files)} qualities)</b>",
        parse_mode="html"
    )

# ================= START =================
@app.on_message(filters.command("start"))
async def start(client, m: Message):
    if not is_owner(m.from_user.id):
        return

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode="html")

        for item in ep["files"]:
            chat, mid = re.search(
                r"https://t\.me/([^/]+)/(\d+)",
                item["link"]
            ).groups()

            src = await client.get_messages(chat, int(mid))

            prog = await m.reply("📥 Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")
            start_t = time.time()
            last_pct = -1

            async def upd(stage, c, t):
                pct = int(c * 100 / t) if t else 0
                nonlocal last_pct
                if pct == last_pct:
                    return
                last_pct = pct
                await prog.edit(
                    f"{stage}\n{bar(pct)} {pct}%\n{speed(c, start_t)}"
                )

            def cb(c, t, stage):
                client.loop.create_task(upd(stage, c, t))

            path = await client.download_media(
                src,
                progress=lambda c,t: cb(c,t,"📥 Downloading")
            )

            await asyncio.sleep(2)  # thumb stability

            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(
                    "Jujutsu Kaisen",
                    "02",
                    "06",
                    ep["overall"],
                    item["quality"]
                ),
                thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                supports_streaming=True,
                parse_mode="html",
                progress=lambda c,t: cb(c,t,"📤 Uploading")
            )

            await prog.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("<b>✅ All qualities uploaded</b>", parse_mode="html")

app.run()
