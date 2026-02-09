# Perfect 01 – Final Stable Edition (PM-based Leech Pickup)

import os, re, asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

OWNERS = {709844068}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "/tmp/thumb.jpg"

app = Client(
    "qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

EP_QUEUE = {}

def is_owner(uid): return uid in OWNERS

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

@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply image ke saath /set_thumb")
    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

@app.on_message(filters.text & filters.regex(r"🎺"))
async def parse_episode(_, m: Message):
    if not is_owner(m.from_user.id): return

    blocks = re.split(r"(?=🎺)", m.text)
    for b in blocks:
        t = re.search(r"🎺\s*(.+)", b)
        e = re.search(r"Episode\s+(\d+)", b)
        if not t or not e: continue

        ep = e.group(1)
        EP_QUEUE[ep] = {"title": t.group(1), "files": []}

        await m.reply(
            f"<b>📥 Episode {ep} queued.\nSend /l1 commands manually in leech GC.</b>",
            parse_mode=ParseMode.HTML
        )

@app.on_message(filters.private & filters.video)
async def pickup(_, m: Message):
    name = m.video.file_name or ""
    ep = re.search(r"\((\d+)\)", name)
    q = re.search(r"(480p|720p|1080p|2160p)", name)
    if not ep or not q: return

    ep = ep.group(1)
    q = q.group(1)

    await app.send_video(
        OWNERS.pop(),
        m.video.file_id,
        caption=caption(ep, q),
        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
        parse_mode=ParseMode.HTML,
        supports_streaming=True
    )

app.run()
