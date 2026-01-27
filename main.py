import os
from pyrogram import Client, filters

# ======================
# ENV REQUIRED
# ======================
API_ID = int(os.environ.get("34639756"))
API_HASH = os.environ.get("a5b55e2dbbdcf65e8912f4be4c13c59d")
BOT_TOKEN = os.environ.get("8236826963:AAFxeATFhm2_GAWfHBwQJWTPTt8o1EvafZg")

# ======================
# BOT CLIENT
# ======================
app = Client(
    name="anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ======================
# BASIC COMMANDS
# ======================
@app.on_message(filters.command("ping"))
async def ping(_, message):
    await message.reply_text("🏓 Pong! Anime Qualifier Bot is alive.")

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "🤖 **Anime Qualifier Bot Ready**\n\n"
        "Commands:\n"
        "/ping – bot status\n"
    )

print("🤖 Bot is starting...")

app.run()
