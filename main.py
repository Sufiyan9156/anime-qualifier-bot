import os
from pyrogram import Client, filters

# ======================
# ENV VARIABLES
# ======================
API_ID = int(os.environ.get("api_id"))
API_HASH = os.environ.get("api_hash")
BOT_TOKEN = os.environ.get("bot_token")

# ======================
# OWNERS (2 ADMINS)
# ======================
OWNERS = {2079844068, 6593273878}

BOT_ACTIVE = True

# ======================
# BOT CLIENT
# ======================
app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ======================
# OWNER CHECK
# ======================
def is_owner(user_id: int):
    return user_id in OWNERS

# ======================
# COMMANDS
# ======================
@app.on_message(filters.command("ping"))
async def ping(_, message):
    await message.reply_text("🏓 Pong! Bot is alive.")

@app.on_message(filters.command("on"))
async def bot_on(_, message):
    global BOT_ACTIVE
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command.")
    BOT_ACTIVE = True
    await message.reply_text("✅ Bot ENABLED")

@app.on_message(filters.command("off"))
async def bot_off(_, message):
    global BOT_ACTIVE
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner only command.")
    BOT_ACTIVE = False
    await message.reply_text("⛔ Bot DISABLED (credits saved)")

@app.on_message(filters.command("start"))
async def start(_, message):
    if not BOT_ACTIVE:
        return
    await message.reply_text(
        "🤖 **Anime Qualifier Bot Ready**\n\n"
        "/ping – status\n"
        "/on – enable bot (owner)\n"
        "/off – disable bot (owner)"
    )

print("🤖 Bot starting...")
app.run()
