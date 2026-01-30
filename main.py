import os, re
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

QUALITY_ORDER = ["480p", "720p", "1080p", "2K"]

# Episode titles (JJK S1)
EP_TITLES = {
    1: "Ryomen Sukuna!!",
    2: "For Myself",
    3: "Girl of Steel",
    4: "Curse Womb Must Die",
    5: "Curse Womb Must Die – II",
    6: "After Rain",
    7: "Assault",
    8: "Boredom",
    9: "Small Fry and Reverse Retribution",
    10: "Idle Transfiguration",
    11: "Narrow-minded",
    12: "To You, Someday",
    13: "Tomorrow",
    14: "Kyoto Sister School Exchange Event – Group Battle 0",
    15: "Kyoto Sister School Exchange Event – Group Battle 1",
    16: "Kyoto Sister School Exchange Event – Group Battle 2",
    17: "Kyoto Sister School Exchange Event – Group Battle 3",
    18: "Sage",
    19: "Black Flash",
    20: "Nonstandard",
    21: "Jujutsu Koshien",
    22: "The Origin of Blind Obedience",
    23: "The Origin of Blind Obedience – II",
    24: "Accomplices"
}

# ================= STORAGE =================
DATA = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
# DATA[anime][season][episode][quality] = link

app = Client("file_to_link_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= HELPERS =================
def is_owner(uid):
    return uid in OWNERS

def parse(filename: str):
    up = filename.upper()

    anime = re.sub(r"S\d+.*", "", filename, flags=re.I)
    anime = re.sub(r"[._]", " ", anime).strip().title()

    sm = re.search(r"S(\d+)", up)
    em = re.search(r"E(\d+)", up)

    if not em:
        raise ValueError("Episode not found")

    season = f"{int(sm.group(1)) if sm else 1:02d}"
    episode = int(em.group(1))

    if "2160" in up or "4K" in up:
        quality = "2K"
    elif "1080" in up:
        quality = "1080p"
    elif "720" in up:
        quality = "720p"
    else:
        quality = "480p"

    return anime, season, episode, quality

# ================= FILE HANDLER =================
@app.on_message(filters.video | filters.document)
async def collect(_, m: Message):
    if not m.from_user or not is_owner(m.from_user.id):
        return

    try:
        anime, season, ep, quality = parse((m.video or m.document).file_name)
    except:
        return await m.reply("❌ Episode info not found")

    link = f"https://t.me/c/{str(m.chat.id)[4:]}/{m.id}"

    DATA[anime][season][ep][quality] = link

    await m.reply(
        f"✅ Stored:\n"
        f"{anime} S{season} E{ep:02d} [{quality}]"
    )

# ================= FINAL TXT =================
@app.on_message(filters.command("final_txt"))
async def final_txt(_, m):
    if not is_owner(m.from_user.id):
        return

    out = []
    for anime in DATA:
        for season in DATA[anime]:
            out.append("=" * 30)
            out.append(f"{anime.upper()} – SEASON {season}")
            out.append("=" * 30 + "\n")

            for ep in sorted(DATA[anime][season]):
                title = EP_TITLES.get(ep, "")
                out.append(f"Episode {ep:03d} – {title}")

                for q in QUALITY_ORDER:
                    if q in DATA[anime][season][ep]:
                        out.append(
                            f"{anime} Season {season} Episode {ep:02d} ({ep:03d}) [{q}] {UPLOAD_TAG}"
                        )
                        out.append(DATA[anime][season][ep][q] + "\n")

                out.append("-" * 32 + "\n")

            out.append(f"END OF {anime.upper()} S{season}")
            out.append("=" * 30)

    await m.reply("\n".join(out)[:4000])

# ================= CLEAR =================
@app.on_message(filters.command("clear"))
async def clear(_, m):
    DATA.clear()
    await m.reply("🗑 Data cleared")

print("🤖 File → Link → TXT Bot READY")
app.run()
