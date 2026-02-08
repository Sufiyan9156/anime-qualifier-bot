import os, re, time, asyncio
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}

LEECH_BOT = "KPSLeech1Bot"   # only l1
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "/tmp/thumb.jpg"

QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================= MEMORY =================
EPISODE_META = {}   # episode -> title
EPISODE_TRACK = defaultdict(dict)  # episode -> {quality: True}

# ================= UTILS =================
def is_owner(uid):
    return uid in OWNERS

# ================= THUMB =================
@app.on_message(filters.command("set_thumb"))
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("Reply image ke saath /set_thumb")

    await app.download_media(m.reply_to_message.photo, THUMB_PATH)
    await m.reply("✅ Thumbnail saved (KPS ke liye ready)")

# ================= PARSER =================
def parse_blocks(text):
    blocks = re.split(r"(?=🎺)", text)
    result = []

    for b in blocks:
        b = b.strip()
        if not b.startswith("🎺"):
            continue

        title_m = re.search(r"🎺\s*(.+)", b)
        ep_m = re.search(r"Episode\s+\d+\((\d+)\)", b)

        if not title_m or not ep_m:
            continue

        episode = int(ep_m.group(1))
        result.append((episode, title_m.group(1), b))

    return result

def extract_links(block):
    links = []
    for m in re.finditer(r"(https://t\.me/\S+).*?\[(480p|720p|1080p|2160p)\]", block):
        links.append((m.group(1), m.group(2)))
    return links

# ================= QUEUE → DISPATCH =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def dispatch(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    blocks = parse_blocks(m.text)
    if not blocks:
        return await m.reply("❌ No valid episode blocks")

    for episode, title, block in blocks:
        EPISODE_META[episode] = title
        links = extract_links(block)

        for link, q in links:
            cmd = f"/l1 {link} -n {title} [{q}] {UPLOAD_TAG}"
            await app.send_message(LEECH_BOT, cmd)
            await asyncio.sleep(1.5)

        await m.reply(
            f"<b>📤 Dispatched → Episode {episode} ({len(links)} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

# ================= KPS PM LISTENER =================
@app.on_message(
    (filters.private) &
    (filters.video | filters.document)
)
async def kps_listener(_, m: Message):
    if not m.from_user:
        return
    if m.from_user.username != LEECH_BOT.lower():
        return

    text = (m.caption or "") + " " + (m.document.file_name if m.document else "")
    ep_m = re.search(r"\((\d{3})\)", text)
    q_m = re.search(r"(480p|720p|1080p|2160p)", text)

    if not ep_m or not q_m:
        return

    episode = int(ep_m.group(1))
    quality = q_m.group(1)

    EPISODE_TRACK[episode][quality] = True

    # ✅ check completion
    done = all(q in EPISODE_TRACK[episode] for q in QUALITY_ORDER)
    if not done:
        return

    # ================= FINAL STATUS MESSAGE =================
    title = EPISODE_META.get(episode, f"Episode {episode}")

    msg = f"<b>🎺 {title}</b>\n"
    for q in QUALITY_ORDER:
        msg += f"{q} (With Renaming, Captioning & Thumbnail Applied)\n"

    await app.send_message(
        "me",
        msg,
        parse_mode=ParseMode.HTML
    )

    # cleanup
    EPISODE_TRACK.pop(episode, None)
    EPISODE_META.pop(episode, None)

# ================= RUN =================
print("🤖 Perfect 01 – Leech Edition Running")
app.run()
