import os
import re
import asyncio
import urllib.request
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "thumb.jpg"

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Sufiyan9156/anime-qualifier-bot/main/episodes"

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# queue[anime][season][episode] = {"title": str, "qualities": {q: [file_id]}}
QUEUE = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
    "title": "",
    "qualities": defaultdict(list)
})))

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

# ================= HELPERS =================
def is_owner(uid): 
    return uid in OWNERS

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def parse_filename(filename):
    name = filename.replace("_", " ").replace(".", " ").lower()

    if "2160" in name or "4k" in name:
        q = "2k"
    elif "1080" in name:
        q = "1080p"
    elif "720" in name:
        q = "720p"
    else:
        q = "480p"

    s, e = 1, 1
    m = re.search(r"s(\d{1,2})\D*e(\d{1,3})", name)
    if m:
        s, e = int(m.group(1)), int(m.group(2))

    clean = re.sub(
        r".*?|s\d+e\d+|\d{3,4}p|4k|hindi|dual|web|hdrip|bluray|x264|x265|aac|mp4|mkv|@\w+",
        "",
        name
    )
    anime = re.sub(r"\s+", " ", clean).strip().title()

    return anime, f"{s:02d}", f"{e:02d}", f"{e:03d}", q

def load_episode_title(anime, season, episode):
    slug = slugify(anime)
    url = f"{GITHUB_RAW_BASE}/{slug}/season_{season}.txt"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            for line in r.read().decode().splitlines():
                if "|" not in line:
                    continue
                ep, title = line.split("|", 1)
                if int(ep.strip()) == episode:
                    return title.strip()
    except:
        pass
    return f"Episode {episode:02d}"

def build_filename(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"

def build_caption(a, s, e, o, q):
    return (
        f"⬡ **{a}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ **Season : {s}**\n"
        f"┃ **Episode : {e}({o})**\n"
        f"┃ **Audio : Hindi #Official**\n"
        f"┃ **Quality : {q}**\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ **Uploaded By {UPLOAD_TAG}**"
    )

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karke /set_thumb bhejo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail saved")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("❌ Thumbnail not set")

# ================= ADD TO QUEUE =================
@app.on_message(filters.video | filters.document)
async def add_queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    anime, s, e, o, q = parse_filename(media.file_name or "video.mp4")
    title = load_episode_title(anime, s, int(e))

    QUEUE[anime][s][e]["title"] = title
    QUEUE[anime][s][e]["qualities"][q].append(media.file_id)

    await m.reply(f"📥 Added → {anime} S{s}E{e} [{q}]")

# ================= PREVIEW =================
@app.on_message(filters.command("preview"))
async def preview(_, m):
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    text = "🧪 **PREVIEW**\n\n"
    for anime, seasons in QUEUE.items():
        text += f"⬡ **{anime}**\n"
        for s, eps in seasons.items():
            text += f"\nSeason {s}\n"
            for e, data in sorted(eps.items()):
                text += f"\n🎺 Episode {e} – {data['title']}\n"
                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    text += f"• {q}\n"
        text += "\n"

    await m.reply(text)

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    await m.reply("🚀 Uploading...")

    for anime, seasons in QUEUE.items():
        for s, eps in seasons.items():
            for e, data in sorted(eps.items()):
                o = f"{int(e):03d}"
                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    for fid in data["qualities"][q]:
                        path = await client.download_media(fid)
                        await client.send_video(
                            m.chat.id,
                            path,
                            caption=build_caption(anime, s, e, o, q),
                            file_name=build_filename(anime, s, e, o, q),
                            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                            supports_streaming=True
                        )
                        os.remove(path)
                        await asyncio.sleep(1)

    QUEUE.clear()
    await m.reply("✅ All uploads done")

# ================= RUN =================
print("🤖 Anime Qualifier Bot — FINAL STABLE BUILD")
app.run()
