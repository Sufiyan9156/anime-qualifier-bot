import os
import re
import asyncio
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

LEECH_GROUP = "TorrentLeechGroup"     # without @
LEECH_BOT = "KPSLeech1Bot"

QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]
UPLOAD_TAG = "@SenpaiAnimess"

# ================= CLIENT =================
app = Client(
    "qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================= MEMORY =================
# episode_no -> { title, qualities{q: False} }
EPISODES = {}
# episode_no -> received qualities set
RECEIVED = defaultdict(set)

# ================= UTILS =================
def is_owner(uid):
    return uid in OWNERS

def extract_quality(name):
    for q in QUALITY_ORDER:
        if q in name:
            return q
    return None

# ================= PARSER =================
def parse_bulk(text):
    blocks = re.split(r"(?=🎺)", text)
    parsed = []

    for block in blocks:
        block = block.strip()
        if not block.startswith("🎺"):
            continue

        title_m = re.search(r"🎺\s*(.+)", block)
        ep_m = re.search(r"Episode\s+(\d+)", block)
        if not title_m or not ep_m:
            continue

        episode_no = int(ep_m.group(1))
        title = title_m.group(1)

        links = re.findall(
            r"(https://t\.me/\S+)\s+-n\s+(.+?\[(480p|720p|1080p|2160p)\])",
            block
        )

        files = []
        for link, fname, q in links:
            files.append({
                "link": link,
                "filename": fname,
                "quality": q
            })

        files.sort(key=lambda x: QUALITY_ORDER.index(x["quality"]))

        parsed.append({
            "episode": episode_no,
            "title": title,
            "files": files
        })

    return sorted(parsed, key=lambda x: x["episode"])

# ================= QUEUE HANDLER =================
@app.on_message(filters.text & filters.regex(r"🎺"))
async def handle_bulk(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    episodes = parse_bulk(m.text)
    if not episodes:
        return await m.reply("❌ No valid episodes found")

    for ep in episodes:
        ep_no = ep["episode"]

        if ep_no not in EPISODES:
            EPISODES[ep_no] = {
                "title": ep["title"],
                "qualities": {q["quality"]: False for q in ep["files"]}
            }

        for item in ep["files"]:
            cmd = f"/l1 {item['link']} -n {item['filename']} {UPLOAD_TAG}"

            try:
                await app.send_message(
                    LEECH_GROUP,
                    cmd
                )
                await asyncio.sleep(2)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)

        await m.reply(
            f"<b>📤 Dispatched → Episode {ep_no} ({len(ep['files'])} qualities)</b>",
            parse_mode=ParseMode.HTML
        )

# ================= FILE LISTENER =================
@app.on_message(filters.private & filters.video)
async def receive_file(_, m: Message):
    if not m.from_user:
        return
    if m.from_user.username != LEECH_BOT:
        return

    name = m.video.file_name or ""
    ep_m = re.search(r"Episode\s+(\d+)", name)
    if not ep_m:
        return

    ep_no = int(ep_m.group(1))
    quality = extract_quality(name)
    if not quality:
        return

    if ep_no not in EPISODES:
        return

    RECEIVED[ep_no].add(quality)

    # check completion
    expected = set(EPISODES[ep_no]["qualities"].keys())
    if RECEIVED[ep_no] == expected:
        lines = [
            f"<b>🎺 Episode {ep_no} – {EPISODES[ep_no]['title']}</b>",
            ""
        ]
        for q in QUALITY_ORDER:
            lines.append(f"<b>{q} ✅ Renamed + Captioned + Thumbnail Applied</b>")

        await m.reply(
            "\n".join(lines),
            parse_mode=ParseMode.HTML
        )

# ================= START =================
print("🤖 QUALIFIER BOT — PERFECT 01 (LEECH MODE)")
app.run()
