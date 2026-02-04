import os
import re
import time
import asyncio
import urllib.request
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024  # 200 KB

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Sufiyan9156/anime-qualifier-bot/main/episodes"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

QUEUE = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
    "title": "",
    "qualities": defaultdict(list)
})))

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean_anime_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"\[.*?]", " ", name)
    name = re.sub(r"s\d{1,2}\s*e\d{1,3}", " ", name)
    name = re.sub(
        r"\b(hindi|dual|multi|world|official|uncut|web|hdrip|bluray|x264|x265|aac|mp4|mkv|sd|hd|fhd|uhd|4k)\b",
        " ",
        name
    )
    name = re.sub(r"\d{3,4}p", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()


def parse_filename(filename):
    raw = filename.replace("_", " ").replace(".", " ").lower()

    if "2160" in raw or "4k" in raw:
        q = "2k"
    elif "1080" in raw:
        q = "1080p"
    elif "720" in raw:
        q = "720p"
    else:
        q = "480p"

    s, e = 1, 1
    m = re.search(r"s(\d{1,2})\D*e(\d{1,3})", raw)
    if m:
        s, e = int(m.group(1)), int(m.group(2))

    anime = clean_anime_name(raw)
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
        f"┃ Season : {s}\n"
        f"┃ Episode : {e}({o})\n"
        f"┃ Audio : Hindi #Official\n"
        f"┃ Quality : {q}\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ Uploaded By {UPLOAD_TAG}"
    )

# ================= THUMB =================

@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    r = m.reply_to_message

    file = None

    if r.photo:
        file = r.photo
    elif r.video and r.video.thumbs:
        file = r.video.thumbs[0]
    elif r.document and r.document.thumbs:
        file = r.document.thumbs[0]

    if not file:
        return await m.reply("❌ Reply with PHOTO or VIDEO thumbnail")

    try:
        await file.download(file_name=THUMB_PATH)
    except Exception as e:
        return await m.reply(f"❌ Thumbnail download failed")

    if not os.path.exists(THUMB_PATH):
        return await m.reply("❌ Thumbnail save failed")

    if os.path.getsize(THUMB_PATH) > 200 * 1024:
        os.remove(THUMB_PATH)
        return await m.reply("❌ Thumbnail must be under 200KB")

    await m.reply("✅ Custom thumbnail saved")
    
# ================= ADD =================
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

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    status = await m.reply("🚀 Uploading...")
    last_text = ""
    last_edit = 0

    for anime, seasons in QUEUE.items():
        for s, eps in seasons.items():
            for e, data in sorted(eps.items()):
                o = f"{int(e):03d}"
                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    for fid in data["qualities"][q]:
                        path = await client.download_media(fid)
                        start = time.time()

                        async def progress(cur, total):
                            nonlocal last_text, last_edit
                            now = time.time()
                            if now - last_edit < 1:
                                return

                            percent = int(cur * 100 / total)
                            speed = (cur / max(1, now - start)) / (1024 * 1024)
                            bar = "■" * (percent // 10) + "▢" * (10 - percent // 10)

                            text = (
                                f"Status: Uploading\n"
                                f"{bar} {percent}%\n"
                                f"⏩ {speed:.2f} MB/s"
                            )

                            if text != last_text:
                                try:
                                    await status.edit(text)
                                    last_text = text
                                    last_edit = now
                                except MessageNotModified:
                                    pass

                        await client.send_video(
                            m.chat.id,
                            path,
                            caption=build_caption(anime, s, e, o, q),
                            file_name=build_filename(anime, s, e, o, q),
                            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                            supports_streaming=True,
                            progress=progress
                        )

                        os.remove(path)
                        await asyncio.sleep(1)

    QUEUE.clear()
    await status.edit("✅ All uploads done")

# ================= RUN =================
print("🤖 Anime Qualifier Bot — FINAL STABLE GOD BUILD")
app.run()
