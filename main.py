import os
import re
import time
import asyncio
import urllib.request
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait

# ================= ENV =================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Sufiyan9156/anime-qualifier-bot/main/episodes"

QUALITY_ORDER = {"480p": 1, "720p": 2, "1080p": 3, "2160p": 4}

# ================= USER CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# queue[anime][season][episode]
QUEUE = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
    "title": "",
    "qualities": {},
    "added_msgs": []
})))

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean_anime_name(raw: str) -> str:
    raw = raw.lower()
    raw = re.sub(r"\[.*?]", " ", raw)
    raw = re.sub(r"@\w+", " ", raw)
    raw = re.sub(r"s\d{1,2}\s*e\d{1,3}", " ", raw)
    raw = re.sub(
        r"\b(hindi|dual|multi|official|uncut|web|hdrip|bluray|x264|x265|aac|sd|hd|fhd|uhd|4k|2160p|1080p|720p|480p|anime|world|offic)\b",
        " ",
        raw
    )
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw.title()


def parse_filename(filename):
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
                if "|" not in line:
                    continue
                ep, title = line.split("|", 1)
                if int(ep.strip()) == episode:
                    return title.strip()
    except:
        pass
    return f"Episode {episode:03d}"


def build_caption(a, s, e, o, q):
    return (
        f"**⬡ {a}**\n"
        f"**╔══════════════════════╗**\n"
        f"**‣ Season : {s}**\n"
        f"**‣ Episode : {e} ({o})**\n"
        f"**‣ Audio : Hindi #Official**\n"
        f"**‣ Quality : {q}**\n"
        f"**╚══════════════════════╝**\n"
        f"**⬡ Uploaded By: {UPLOAD_TAG}**"
    )


def build_filename(a, s, e, o, q):
    return f"{a} Season {s} Episode {e}({o}) [{q}] {UPLOAD_TAG}.mp4"


# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply("❌ **Reply with PHOTO only**")

    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)

    await client.download_media(m.reply_to_message.photo, file_name=THUMB_PATH)

    if not os.path.isfile(THUMB_PATH):
        return await m.reply("❌ **Thumbnail save failed**")

    if os.path.getsize(THUMB_PATH) > MAX_THUMB_SIZE:
        os.remove(THUMB_PATH)
        return await m.reply("❌ **Thumbnail must be under 200KB**")

    await m.reply("✅ **Custom thumbnail saved**")


# ================= ADD =================
@app.on_message(filters.video | filters.document)
async def add_queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    anime, s, e, o, q = parse_filename(media.file_name or "video.mp4")

    title = load_episode_title(anime, s, int(e))
    QUEUE[anime][s][e]["title"] = title
    QUEUE[anime][s][e]["qualities"][q] = media.file_id

    msg = await m.reply(f"**📥 Added → {anime} S{s}E{e} [{q}]**")
    QUEUE[anime][s][e]["added_msgs"].append(msg)


# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client: Client, m: Message):
    if not is_owner(m.from_user.id):
        return

    status = await m.reply("**🚀 Uploading...**")

    for anime, seasons in QUEUE.items():
        for s, eps in seasons.items():
            for e, data in sorted(eps.items()):
                o = f"{int(e):03d}"

                # episode summary
                lines = [f"**🎺 Episode {o} - {data['title']}**"]
                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    lines.append(f"**{q}**")
                await m.reply("\n".join(lines))

                # delete added msgs
                for msg in data["added_msgs"]:
                    try:
                        await msg.delete()
                    except:
                        pass

                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    fid = data["qualities"][q]
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
    await status.edit("✅ **All uploads done**")


print("🤖 Anime Qualifier — FINAL USER SESSION GOD MODE")
app.run()
