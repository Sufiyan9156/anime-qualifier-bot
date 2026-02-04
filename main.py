import os
import re
import json
import asyncio
import urllib.request
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message

# ================== ENV ==================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ================== CONFIG ==================
OWNERS = {709844068, 6593273878}
UPLOAD_TAG = "@SenpaiAnimess"
THUMB_PATH = "thumb.jpg"

# GitHub raw base (change only repo/user if needed)
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO/main/episodes"

# ================== BOT ==================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================== GLOBAL QUEUE ==================
# STRUCTURE:
# queue[anime][season][episode] = {
#   "title": "...",
#   "qualities": { "480p": [file_id, ...], ... }
# }
QUEUE = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
    "title": None,
    "qualities": defaultdict(list)
})))

# ================== HELPERS ==================
def is_owner(uid: int) -> bool:
    return uid in OWNERS


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


# -------- Filename Analyzer --------
def parse_filename(filename: str):
    name = filename.lower()

    # Quality
    if "2160" in name or "4k" in name:
        quality = "2160p"
    elif "1080" in name:
        quality = "1080p"
    elif "720" in name:
        quality = "720p"
    else:
        quality = "480p"

    # Season / Episode
    s, e = 1, 1
    m = re.search(r"s(\d{1,2})\D*e(\d{1,3})", name)
    if m:
        s, e = int(m.group(1)), int(m.group(2))

    # Clean anime name
    clean = re.sub(
        r"\[.*?\]|s\d+e\d+|\d{3,4}p|4k|hindi|dual|web|hdrip|bluray|x264|x265|aac|mp4|mkv|@\w+",
        "",
        name
    )
    anime_guess = re.sub(r"\s+", " ", clean).strip().title()

    return anime_guess, f"{s:02d}", f"{e:02d}", f"{e:03d}", quality


# -------- AniList Normalize (NO API KEY NEEDED) --------
def anilist_normalize(title: str) -> str:
    query = {
        "query": """
        query ($search: String) {
          Media(search: $search, type: ANIME) {
            title {
              english
              romaji
            }
          }
        }
        """,
        "variables": {"search": title}
    }

    try:
        req = urllib.request.Request(
            "https://graphql.anilist.co",
            data=json.dumps(query).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            media = data.get("data", {}).get("Media")
            if not media:
                return title
            return media["title"]["english"] or media["title"]["romaji"] or title
    except:
        return title


# -------- Episode Title Loader (GitHub TXT) --------
def load_episode_title(anime: str, season: str, episode: int):
    slug = slugify(anime)
    url = f"{GITHUB_RAW_BASE}/{slug}/season_{season}.txt"

    try:
        with urllib.request.urlopen(url, timeout=10) as res:
            lines = res.read().decode().splitlines()
            for line in lines:
                if "|" not in line:
                    continue
                ep_no, title = line.split("|", 1)
                if int(ep_no.strip()) == episode:
                    return title.strip()
    except:
        pass

    return f"Episode {episode:02d}"


# -------- Builders --------
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


# ================== THUMB ==================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("❌ Photo ko reply karo")

    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Custom Thumbnail saved")


@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m: Message):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH, caption="🖼️ Current Thumbnail")
    else:
        await m.reply("❌ Thumbnail not set")


# ================== ADD TO QUEUE ==================
@app.on_message(filters.video | filters.document)
async def add_to_queue(_, m: Message):
    if not is_owner(m.from_user.id):
        return

    media = m.video or m.document
    fname = media.file_name or "video.mp4"

    anime_guess, s, e, o, q = parse_filename(fname)
    anime = anilist_normalize(anime_guess)

    ep_title = load_episode_title(anime, s, int(e))

    entry = QUEUE[anime][s][e]
    entry["title"] = ep_title
    entry["qualities"][q].append(media.file_id)

    await m.reply(f"📥 Added → {anime} S{s}E{e} [{q}]")


# ================== PREVIEW ==================
@app.on_message(filters.command("preview"))
async def preview(_, m: Message):
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    text = "🧪 **PREVIEW (Grouped)**\n\n"

    for anime, seasons in QUEUE.items():
        text += f"⬡ **{anime}**\n"
        for s, episodes in seasons.items():
            text += f"\nSeason {s}\n"
            for e, data in sorted(episodes.items()):
                text += f"\n🎺 Episode {e} – {data['title']}\n"
                for q in sorted(data["qualities"].keys()):
                    text += f"• {q}\n"
        text += "\n"

    await m.reply(text)


# ================== START UPLOAD ==================
@app.on_message(filters.command("start"))
async def start_upload(client, m: Message):
    if not is_owner(m.from_user.id):
        return
    if not QUEUE:
        return await m.reply("❌ Queue empty")

    await m.reply("🚀 Uploading videos...")

    for anime, seasons in QUEUE.items():
        for s, episodes in seasons.items():
            for e, data in sorted(episodes.items()):
                o = f"{int(e):03d}"
                for q, file_ids in data["qualities"].items():
                    for fid in file_ids:
                        path = await client.download_media(fid)

                        await client.send_video(
                            chat_id=m.chat.id,
                            video=path,
                            caption=build_caption(anime, s, e, o, q),
                            file_name=build_filename(anime, s, e, o, q),
                            thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                            supports_streaming=True
                        )

                        os.remove(path)
                        await asyncio.sleep(1)

    QUEUE.clear()
    await m.reply("✅ All uploads done")


# ================== RUN ==================
print("🤖 Anime Qualifier Bot — FINAL PRODUCTION BUILD")
app.run()
