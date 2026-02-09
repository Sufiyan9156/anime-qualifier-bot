import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageIdInvalid

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

# ================= UTILS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS

def z2(n: int) -> str:
    return f"{n:02d}"

def z3(n: int) -> str:
    return f"{n:03d}"

def bar(p: int) -> str:
    f = p // 10
    return "▰" * f + "▱" * (10 - f)

def speed(done: int, start: float) -> str:
    t = max(1, time.time() - start)
    return f"{done / t / (1024 * 1024):.2f} MB/s"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply image ke saath /set_thumb")
    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail set")

# ================= PARSER (LENIENT) =================
def parse_message(text: str):
    episodes = []
    blocks = re.split(r"🎺", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        title_m = re.search(r"Episode\s+(\d+)\s*-\s*(.+)", block)
        if not title_m:
            continue

        overall = int(title_m.group(1))
        title = title_m.group(2).strip()

        files = []
        for link, name, q in re.findall(
            r"(https://t\.me/\S+)\s+-n\s+(.+?)\s+\[(480p|720p|1080p|2160p)\]",
            block,
            flags=re.I
        ):
            files.append({
                "link": link,
                "name": name,
                "quality": q
            })

        files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

        if files:
            episodes.append({
                "overall": overall,
                "title": title,
                "files": files
            })

    return episodes

# ================= CAPTION =================
def caption(anime, season, ep, overall, quality):
    return (
        f"<b>⬡ {anime}</b>\n"
        f"<b>╔══════════════════════╗</b>\n"
        f"<b>‣ Season : {z2(season)}</b>\n"
        f"<b>‣ Episode : {z2(ep)} ({z3(overall)})</b>\n"
        f"<b>‣ Audio : Hindi #Official</b>\n"
        f"<b>‣ Quality : {quality}</b>\n"
        f"<b>╚══════════════════════╝</b>\n"
        f"<b>⬡ Uploaded By : {UPLOAD_TAG}</b>"
    )

# ================= HANDLER =================
@app.on_message((filters.text | filters.caption) & filters.regex("🎺"))
async def handle(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text or m.caption
    episodes = parse_message(text)

    if not episodes:
        return await m.reply("❌ No valid episode found")

    for ep in episodes:
        # 🔹 Title ONCE
        await m.reply(
            f"<b>🎺 Episode {z3(ep['overall'])} – {ep['title']}</b>",
            parse_mode=ParseMode.HTML
        )

        for f in ep["files"]:
            chat, mid = re.search(
                r"https://t\.me/([^/]+)/(\d+)",
                f["link"]
            ).groups()

            src = await app.get_messages(chat, int(mid))
            prog = await m.reply("📥 Downloading...")
            start_t = time.time()
            last_edit = 0

            async def safe_edit(t):
                nonlocal last_edit
                if time.time() - last_edit < 3:
                    return
                last_edit = time.time()
                try:
                    await prog.edit(t)
                except:
                    pass

            def cb(c, t, stage):
                p = int(c * 100 / t) if t else 0
                app.loop.create_task(
                    safe_edit(f"{stage}\n{bar(p)} {p}%\n{speed(c, start_t)}")
                )

            path = await app.download_media(
                src,
                progress=lambda c, t: cb(c, t, "📥 Downloading")
            )

            while True:
                try:
                    await app.send_video(
                        m.chat.id,
                        path,
                        caption=caption(
                            "Jujutsu Kaisen",
                            1,
                            ep["overall"],
                            ep["overall"],
                            f["quality"]
                        ),
                        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                        supports_streaming=True,
                        parse_mode=ParseMode.HTML,
                        progress=lambda c, t: cb(c, t, "📤 Uploading")
                    )
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)

            try:
                await prog.delete()
            except:
                pass

            os.remove(path)

    await m.reply("<b>✅ All uploads completed</b>", parse_mode=ParseMode.HTML)

# ================= RUN =================
app.run()
