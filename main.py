from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "anime_qualifier_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message()
async def alive(_, message):
    await message.reply_text("✅ Anime Qualifier Bot is alive!")

print("🤖 Bot starting...")
app.run()
