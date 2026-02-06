import os
import re
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"

# ================= USER CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================= HELPERS =================
def is_owner(uid: int) -> bool:
    return uid in OWNERS


# ================= THUMB COMMANDS =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ Reply with PHOTO only")

    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)

    await client.download_media(m.reply_to_message.photo, file_name=THUMB_PATH)
    await m.reply("✅ Thumbnail saved")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("❌ Thumbnail not set")


@app.on_message(filters.command("delete_thumb"))
async def delete_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
        await m.reply("✅ Thumbnail deleted")
    else:
        await m.reply("❌ No thumbnail found")


# ================= TEXT PARSER =================
@app.on_message(filters.text & ~filters.command([]))
async def parse_episode_text(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    text = m.text.strip()

    # 🎺 Episode 025 - Hidden Inventory
    header = re.search(r"🎺\s*Episode\s+(\d+).*?-\s*(.+)", text)
    if not header:
        return

    overall_ep = header.group(1)
    title = header.group(2).strip()

    # All quality lines
    qualities = re.findall(
        r"-n\s+(Jujutsu.+?\[(480p|720p|1080p|2160p)\]\s+@SenpaiAnimess)",
        text,
        re.IGNORECASE
    )

    if not qualities:
        return await m.reply("❌ No quality links found")

    # Build final output
    output = [f"🎺 **Episode {overall_ep} - {title}**\n"]
    for q in qualities:
        output.append(q[0])

    await m.reply("\n".join(output))


# ================= RUN =================
print("🤖 Anime Qualifier — FINAL STABLE BUILD RUNNING")
app.run()
