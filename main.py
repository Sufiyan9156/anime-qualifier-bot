import os
import re
import time
import asyncio
import urllib.request
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

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

# ================= QUEUE =================
QUEUE = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
    "title": "",
    "qualities": defaultdict(list)
})))

# ================= HELPERS =================
def is_owner(uid: int):
    return uid in OWNERS


def slugify(text: str):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean_anime_name(name: str):
    name = name.lower()
    name = re.sub(
        r"\[.*?\]|s\d+e\d+|\d{3,4}p|2160p|4k|1080p|720p|480p|"
        r"hindi|dual|multi|web|hdrip|bluray|x264|x265|aac|sd|hd|"
        r"mp4|mkv|@\w+",
        "",
        name
    )
    name = re.sub(r"[_\.]", " ", name)
    return re.sub(r"\s+", " ", name).strip().title()


def parse_filename(filename: str):
    raw = filename.replace("_", " ").replace(".", " ").lower()

    if "2160" in raw or "4k" in raw:
        q = "2160p"
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
                if "|" in line:
                    ep, title = line.split("|", 1)
                    if int(ep.strip()) == episode:
                        return title.strip()
    except:
        pass

    return f"Episode {episode:02d}"


def build_filename(anime, s, e, o, q):
    return f"{anime} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"


def build_caption(anime, s, e, o, q):
    return (
        f"⬡ **{anime}**\n"
        f"┏━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ Season : {s}\n"
        f"┃ Episode : {e}({o})\n"
        f"┃ Audio : Hindi #Official\n"
        f"┃ Quality : {q}\n"
        f"┗━━━━━━━━━━━━━━━━━━┛\n"
        f"⬡ Uploaded By {UPLOAD_TAG}"
    )


def human_speed(bytes_done, seconds):
    if seconds == 0:
        return "0 MB/s"
    return f"{(bytes_done / seconds) / (1024*1024):.2f} MB/s"


# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karo")

    file = await m.reply_to_message.download()
    os.rename(file, THUMB_PATH)
    await m.reply("✅ Custom Thumbnail saved")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
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
async def preview(_, m: Message):
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    text = "🧪 **PREVIEW (Grouped)**\n\n"
    for anime, seasons in QUEUE.items():
        text += f"⬡ **{anime}**\n"
        for s, eps in seasons.items():
            text += f"\nSeason {s}\n"
            for e, data in sorted(eps.items()):
                text += f"\n🎺 Episode {e} – {data['title']}\n"
                for q in sorted(data["qualities"]):
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

    status = await m.reply("🚀 Starting uploads...")

    for anime, seasons in QUEUE.items():
        for s, eps in seasons.items():
            for e, data in sorted(eps.items()):
                o = f"{int(e):03d}"
                for q in sorted(data["qualities"]):
                    for fid in data["qualities"][q]:

                        start = time.time()
                        path = await client.download_media(
                            fid,
                            progress=lambda cur, total: asyncio.create_task(
                                status.edit(
                                    f"⬇️ Downloading...\n"
                                    f"{(cur/total)*100:.1f}% | {human_speed(cur, time.time()-start)}"
                                )
                            )
                        )

                        start = time.time()
                        await client.send_video(
                            m.chat.id,
                            path,
                            caption=build_caption(anime, s, e, o, q),
                            file_name=build_filename(anime, s, e, o, q),
                            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                            supports_streaming=True,
                            progress=lambda cur, total: asyncio.create_task(
                                status.edit(
                                    f"⬆️ Uploading...\n"
                                    f"{(cur/total)*100:.1f}% | {human_speed(cur, time.time()-start)}"
                                )
                            )
                        )

                        os.remove(path)
                        await asyncio.sleep(1)

    QUEUE.clear()
    await status.edit("✅ All uploads done")


# ================= RUN =================
print("🤖 Anime Qualifier Bot — GOD MODE FINAL LIVE")
app.run()
