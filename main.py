import os, re, asyncio, tempfile
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

# ================= CONFIG =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

SESSION = "session"  # user session
UPLOAD_TAG = "@SenpaiAnimess"
OWNER_ID = 709844068

THUMB_PATH = "thumb.jpg"

client = TelegramClient(SESSION, API_ID, API_HASH)

# ================= SMART PARSER =================
def parse_filename(name: str):
    original = name.replace("_", " ").replace(".", " ")

    # QUALITY
    if re.search(r"(2160|4K)", original, re.I):
        quality = "2k"
    elif re.search(r"1080", original):
        quality = "1080p"
    elif re.search(r"720", original):
        quality = "720p"
    else:
        quality = "480p"

    # SEASON / EP
    s, e = "01", "01"
    m = re.search(r"S(\d{1,2}).*E(\d{1,3})", original, re.I)
    if m:
        s, e = m.group(1), m.group(2)

    season = f"{int(s):02d}"
    episode = f"{int(e):02d}"
    overall = f"{int(e):03d}"

    # CLEAN ANIME NAME (STRICT)
    anime = re.sub(
        r"(S\d+.*E\d+|EP\s*\d+|\d{3,4}P|HD|FHD|SD|HDRIP|WEB|HINDI|DUAL|MKV|MP4|\[.*?\]|@[\w_]+)",
        "",
        original,
        flags=re.I
    )
    anime = re.sub(r"\s+", " ", anime).strip().title()

    return anime, season, episode, overall, quality

def build_filename(i):
    return (
        f"{i['anime']} Season {i['season']} "
        f"Episode {i['episode']} ({i['overall']}) "
        f"[{i['quality']}] {UPLOAD_TAG}.mp4"
    )

def build_caption(i):
    return (
        f"⬡ **{i['anime']}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {i['season']}**\n"
        f"┃ **Episode : {i['episode']}({i['overall']})**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {i['quality']}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By {UPLOAD_TAG}**"
    )

# ================= COMMANDS =================
@client.on(events.NewMessage(from_users=OWNER_ID, pattern="/set_thumb"))
async def set_thumb(e):
    if not e.reply_to_msg_id:
        await e.reply("❌ Reply to thumbnail image")
        return

    msg = await e.get_reply_message()
    if not msg.photo:
        await e.reply("❌ Photo required")
        return

    await client.download_media(msg.photo, THUMB_PATH)
    await e.reply("✅ Thumbnail saved permanently")

@client.on(events.NewMessage(from_users=OWNER_ID, pattern="/view_thumb"))
async def view_thumb(e):
    if os.path.exists(THUMB_PATH):
        await client.send_file(e.chat_id, THUMB_PATH, caption="🖼 Current Thumbnail")
    else:
        await e.reply("❌ Thumbnail not set")

# ================= MAIN HANDLER =================
@client.on(events.NewMessage(from_users=OWNER_ID))
async def handler(e):
    if not e.file:
        return

    info = parse_filename(e.file.name or "video.mp4")
    anime, season, episode, overall, quality = info

    meta = {
        "anime": anime,
        "season": season,
        "episode": episode,
        "overall": overall,
        "quality": quality
    }

    filename = build_filename(meta)
    caption = build_caption(meta)

    with tempfile.TemporaryDirectory() as tmp:
        path = await e.download_media(file=tmp)

        await client.send_file(
            e.chat_id,
            path,
            caption=caption,
            file_name=filename,
            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
            attributes=[DocumentAttributeVideo(0, 0, 0, supports_streaming=True)]
        )

        await e.reply(f"✅ Uploaded:\n{filename}")

# ================= START =================
print("🔥 Telethon Hybrid Anime Uploader — READY")
client.start()
client.run_until_disconnected()
