import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# ===== LOAD ENV =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
STRING_SESSION = os.environ["STRING_SESSION"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ===== USER CLIENT (FAST) =====
user = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    device_model="Hybrid-Leech",
    system_version="FastMode",
    app_version="1.0",
    flood_sleep_threshold=0
)

# ===== BOT CLIENT =====
bot = TelegramClient(
    "bot",
    API_ID,
    API_HASH
).start(bot_token=BOT_TOKEN)

# ===== MAIN LOGIC =====
async def main():
    me = await user.get_me()
    print(f"✅ USER READY : {me.first_name}")
    print("🚀 SPEED MODE ENABLED (TERMUX)")
    await bot.run_until_disconnected()

async def start():
    await user.start()
    await main()

if __name__ == "__main__":
    asyncio.run(start())
