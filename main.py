import os
import re
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

EPISODE_QUEUE = []

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def make_bar(p):
    f = int(p // 10)
    return "▰" * f + "▱" * (10 - f)

def speed_fmt(done, start):
    elapsed = max(1, time.time() - start)
    return f"{done / elapsed / (1024*1024):.2f} MB/s"

def parse_tme_link(link):
    m = re.search(r"https://t\.me/([^/]+)/(\d+)", link)
    return (m.group(1), int(m.group(2))) if m else (None, None)

async def safe_get_message(client, link):
    chat, mid = parse_tme_link(link)
    try:
        await client.get_chat(chat)
        return await client.get_messages(chat, mid)
    except:
        return None

# ================= CAPTION =================
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

# ================= QUEUE =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def queue_episode(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text

    # 🎺 TITLE
    t = re.search(r"🎺\s*(Episode\s+\d+\s+–\s+.+)", text)
    if not t:
        return

    title = f"<b>🎺 {t.group(1)}</b>"
    overall = re.search(r"Episode\s+(\d+)", t.group(1)).group(1)

    # 🔥 FIND ALL FILES (LINE-INDEPENDENT)
    matches = re.findall(
        r"(https://t\.me/\S+)\s+-n\s+([^\[]+\[(?:480p|720p|1080p|2160p)\][^\n]*)",
        text
    )

    files = []
    for link, name in matches:
        q = next((x for x in QUALITY_ORDER if x in name), "480p")
        files.append({
            "link": link,
            "filename": name.strip(),
            "quality": q
        })

    files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

    EPISODE_QUEUE.append({
        "title": title,
        "overall": overall,
        "files": files
    })

    await m.reply(
        f"📥 Queued → Episode {overall} ({len(files)} qualities)",
        parse_mode=ParseMode.HTML
    )

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    for ep in EPISODE_QUEUE:
        await m.reply(ep["title"], parse_mode=ParseMode.HTML)

        for item in ep["files"]:
            src = await safe_get_message(client, item["link"])
            if not src:
                continue

            prog = await m.reply("📥 Downloading...\n▱▱▱▱▱▱▱▱▱▱ 0%")
            start = time.time()
            last = 0

            async def progress(cur, total, stage):
                nonlocal last
                if time.time() - last < 2:
                    return
                last = time.time()
                pct = cur * 100 / total if total else 0
                await prog.edit(
                    f"{stage}\n{make_bar(pct)} {int(pct)}%\n⏩ {speed_fmt(cur, start)}"
                )

            path = await client.download_media(
                src,
                progress=lambda c, t: progress(c, t, "📥 Downloading")
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
                file_name=item["filename"],
                supports_streaming=False,
                progress=lambda c, t: progress(c, t, "📤 Uploading"),
                parse_mode=ParseMode.HTML
            )

            await prog.delete()
            os.remove(path)

    EPISODE_QUEUE.clear()
    await m.reply("✅ <b>All qualities uploaded</b>", parse_mode=ParseMode.HTML)

print("🤖 Anime Qualifier — MULTI QUALITY FIXED")
app.run()
