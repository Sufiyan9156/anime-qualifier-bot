import os
import re
import urllib.request
from collections import defaultdict
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

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Sufiyan9156/anime-qualifier-bot/main/episodes"

QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]

# ================= CLIENT =================
app = Client(
    "anime_qualifier_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# anime -> season -> episode -> data
QUEUE = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
    "title": "",
    "links": {}
})))

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

def parse_line(text):
    q = "480p"
    if "2160" in text or "4k" in text:
        q = "2160p"
    elif "1080" in text:
        q = "1080p"
    elif "720" in text:
        q = "720p"

    m = re.search(r"season\s*(\d+).*?episode\s*(\d+)", text, re.I)
    if not m:
        return None

    season = f"{int(m.group(1)):02d}"
    ep = f"{int(m.group(2)):02d}"

    anime = re.sub(r"\[.*?]|@\w+|season.*|episode.*", "", text, flags=re.I)
    anime = re.sub(r"\s+", " ", anime).strip().title()

    link = text.split()[0]
    return anime, season, ep, q, link

def load_episode_title(anime, season, ep):
    slug = slugify(anime)
    url = f"{GITHUB_RAW_BASE}/{slug}/season_{season}.txt"
    try:
        with urllib.request.urlopen(url) as r:
            for line in r.read().decode().splitlines():
                n, t = line.split("|", 1)
                if int(n) == int(ep):
                    return t.strip()
    except:
        pass
    return f"Episode {ep}"

def build_caption(anime, season, ep, overall, q):
    return (
        f"⬡ {anime}\n"
        f"╔══════════════════════╗\n"
        f"‣ Season : {season}\n"
        f"‣ Episode : {ep} ({overall})\n"
        f"‣ Audio : Hindi #Official\n"
        f"‣ Quality : {q}\n"
        f"╚══════════════════════╝\n"
        f"⬡ Uploaded By: {UPLOAD_TAG}"
    )

def build_filename(anime, season, ep, overall, q):
    return f"{anime} Season {season} Episode {ep}({overall}) [{q}] {UPLOAD_TAG}.mp4"

# ================= THUMB =================
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(_, m):
    if not is_owner(m.from_user.id):
        return
    if not m.reply_to_message.photo:
        return await m.reply("Reply with photo")
    await m.reply_to_message.download(THUMB_PATH)
    await m.reply("✅ Thumbnail set")

@app.on_message(filters.command("view_thumb"))
async def view_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        await m.reply_photo(THUMB_PATH)
    else:
        await m.reply("No thumbnail")

@app.on_message(filters.command("delete_thumb"))
async def delete_thumb(_, m):
    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
        await m.reply("🗑 Thumbnail deleted")

# ================= COLLECT LINKS =================
@app.on_message(filters.text & ~filters.command)
async def collect(_, m):
    if not is_owner(m.from_user.id):
        return

    parsed = parse_line(m.text)
    if not parsed:
        return

    anime, season, ep, q, link = parsed
    title = load_episode_title(anime, season, ep)

    QUEUE[anime][season][ep]["title"] = title
    QUEUE[anime][season][ep]["links"][q] = link

# ================= START =================
@app.on_message(filters.command("start"))
async def start(_, m):
    if not is_owner(m.from_user.id):
        return

    for anime, seasons in QUEUE.items():
        for season, eps in seasons.items():
            for ep, data in sorted(eps.items()):
                overall = f"{int(ep):03d}"
                await m.reply(f"🎺 Episode {overall} - {data['title']}")

                for q in QUALITY_ORDER:
                    if q not in data["links"]:
                        continue

                    src = data["links"][q]
                    msg = await app.get_messages(src.split("/")[-2], int(src.split("/")[-1]))
                    path = await msg.download()

                    await app.send_video(
                        m.chat.id,
                        path,
                        caption=build_caption(anime, season, ep, overall, q),
                        file_name=build_filename(anime, season, ep, overall, q),
                        thumb=THUMB_PATH if os.path.exists(THUMB_PATH) else None,
                        supports_streaming=True
                    )
                    os.remove(path)

    QUEUE.clear()
    await m.reply("✅ Done")

print("Anime Qualifier FINAL READY")
app.run()
