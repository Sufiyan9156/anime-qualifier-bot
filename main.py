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

def is_owner(uid): return uid in OWNERS

def make_bar(p):
    f = int(p // 10)
    return "▰"*f + "▱"*(10-f)

def speed_fmt(done, start):
    t = max(1, time.time() - start)
    return f"{done / t / (1024*1024):.2f} MB/s"

def extract_files(text):
    results = []
    parts = re.split(r"(https://t\.me/\S+)", text)

    for i in range(1, len(parts), 2):
        link = parts[i]
        tail = parts[i+1] if i+1 < len(parts) else ""

        m = re.search(r"-n\s+([^\[]+\[(480p|720p|1080p|2160p)\][^@\n]*)", tail)
        if not m:
            continue

        results.append({
            "link": link,
            "filename": m.group(1).strip(),
            "quality": m.group(2)
        })

    return results

def build_caption(filename, quality, overall):
    anime, season, ep = re.search(
        r"(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)", filename
    ).groups()

    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>‣ Season : {season.zfill(2)}</b>\n"
        f"<b>‣ Episode : {ep.zfill(2)} ({overall})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

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
        "title": f"<b>🎺 {t.group(1)}</b>",
        "overall": overall,
        "files": files
    })

    await m.reply(
        f"📥 Queued → Episode {overall} ({len(files)} qualities)",
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)

        for item in ep["files"]:
            chat, mid = re.search(r"https://t\.me/([^/]+)/(\d+)", item["link"]).groups()
            msg = await client.get_messages(chat, int(mid))

            prog = await m.reply("📥 Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")
            start = time.time()
            last = 0

            async def progress(c, t, stage):
                nonlocal last
                if time.time() - last < 1.5:
                    return
                last = time.time()
                p = c*100/t if t else 0
                await prog.edit(
                    f"{stage}\n{make_bar(p)} {int(p)}%\n⏩ {speed_fmt(c, start)}"
                )

            path = await client.download_media(
                msg,
                progress=lambda c,t: progress(c,t,"📥 Downloading")
            )

            start = time.time()
            await client.send_video(
                m.chat.id,
                path,
                caption=build_caption(item["filename"], item["quality"], ep["overall"]),
                supports_streaming=False,
                progress=lambda c,t: progress(c,t,"📤 Uploading"),
                parse_mode=ParseMode.HTML
            )

            await prog.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("✅ <b>All qualities uploaded</b>", parse_mode=ParseMode.HTML)

print("🤖 Anime Qualifier — FINAL MULTI QUALITY STABLE")
app.run()
