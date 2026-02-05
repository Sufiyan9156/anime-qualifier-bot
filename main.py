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
SESSION_STRING = os.environ["SESSION_STRING"]

# ================= CONFIG =================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"

THUMB_PATH = "/tmp/thumb.jpg"
MAX_THUMB_SIZE = 200 * 1024

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Sufiyan9156/anime-qualifier-bot/main/episodes"

QUALITY_ORDER = {
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "2160p": 4
}

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
    "qualities": defaultdict(list),
    "add_msgs": []
})))

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def clean_anime_name(raw):
    raw = raw.lower()
    raw = re.sub(r"\[.*?]", " ", raw)
    raw = re.sub(r"@\w+", " ", raw)
    raw = re.sub(r"s\d{1,2}\s*e\d{1,3}", " ", raw)
    raw = re.sub(r"\b(480p|720p|1080p|2160p|4k|hindi|dual|multi|web|bluray|x264|x265|aac|mp4|mkv)\b", " ", raw)
    return re.sub(r"\s+", " ", raw).strip().title()


def parse_filename(name):
    raw = name.replace("_", " ").replace(".", " ").lower()

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
    return anime, f"{s:02d}", f"{e:02d}", f"{int(e):03d}", q


def load_episode_title(anime, season, episode):
    url = f"{GITHUB_RAW_BASE}/{slugify(anime)}/season_{season}.txt"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            for line in r.read().decode().splitlines():
                if "|" in line:
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

# ================= ADD =================
@app.on_message(filters.video | filters.document)
async def add_queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    anime, s, e, o, q = parse_filename((m.video or m.document).file_name or "")
    title = load_episode_title(anime, s, int(e))

    QUEUE[anime][s][e]["title"] = title
    QUEUE[anime][s][e]["qualities"][q].append((m.video or m.document).file_id)
    QUEUE[anime][s][e]["add_msgs"].append(m.id)

    await m.reply(f"**📥 Added → {anime} S{s}E{e} [{q}]**")

# ================= START =================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return

    for anime, seasons in QUEUE.items():
        for s, eps in seasons.items():
            for e, data in sorted(eps.items()):
                o = f"{int(e):03d}"

                # EP TITLE (ONCE)
                lines = [f"**🎺 Episode {o} - {data['title']}**"]
                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    lines.append(f"**{q}**")

                await m.reply("\n".join(lines))

                progress_msg = await m.reply("**Status: Downloading**")

                for q in sorted(data["qualities"], key=lambda x: QUALITY_ORDER[x]):
                    for fid in data["qualities"][q]:

                        start = time.time()

                        async def progress(cur, total):
                            percent = int(cur * 100 / total)
                            speed = (cur / max(1, time.time() - start)) / (1024 * 1024)
                            bar = "■" * (percent // 10) + "▢" * (10 - percent // 10)
                            text = f"**Status: Uploading**\n**{bar} {percent}%**\n**⏫ {speed:.2f} MB/s**"
                            try:
                                await progress_msg.edit(text)
                            except MessageNotModified:
                                pass

                        path = await client.download_media(fid)
                        await client.send_video(
                            m.chat.id,
                            path,
                            caption=build_caption(anime, s, e, o, q),
                            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                            supports_streaming=True,
                            progress=progress
                        )
                        os.remove(path)

                await progress_msg.delete()

                for mid in data["add_msgs"]:
                    try:
                        await client.delete_messages(m.chat.id, mid)
                    except:
                        pass

    QUEUE.clear()
    await m.reply("✅ **All uploads done**")

print("🤖 Anime Qualifier — FINAL CLEAN BUILD LIVE")
app.run()
