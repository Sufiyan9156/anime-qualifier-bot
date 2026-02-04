import os
import re
import time
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

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2k": 4}

# ================= BOT =================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# queue[anime][season][episode]
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
    if not m.reply_to_message.photo:
        return await m.reply("❌ Reply image with /set_thumb")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Custom thumbnail saved")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼 Current Thumbnail")
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

    text = "🧪 **PREVIEW (Grouped)**\n\n"
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

    status = await m.reply("🚀 Uploading...")
    start_time = time.time()

    for anime, seasons in QUEUE.items():
        for s, eps in seasons.items():
            for e, data in sorted(eps.items()):
                o = f"{int(e):03d}"
                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    for fid in data["qualities"][q]:
                        path = await client.download_media(fid)

                        file_size = os.path.getsize(path)
                        sent = 0

                        async def progress(cur, total):
                            nonlocal sent
                            sent = cur
                            percent = int(cur * 100 / total)
                            speed = cur / max(1, (time.time() - start_time)) / (1024 * 1024)
                            bar = "■" * (percent // 10) + "▢" * (10 - percent // 10)
                            await status.edit(
                                f"Status: Uploading\n"
                                f"{bar} {percent}%\n"
                                f"⏩ {speed:.2f} MB/s"
                            )

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
print("🤖 Anime Qualifier Bot — GOD MODE BUILD LIVE")
app.run()
