import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# ====== CONFIG (DIRECT) ======

API_ID = 34639756
API_HASH = "a5b55e2dbbdcf65e8912f4be4c13c59d"

BOT_TOKEN = "8236826963:AAFxeATFhm2_GAWfHBwQJWTPTt8o1EvafZg"

STRING_SESSION = "IBVts0JwBuzh5rfw34Wqomc2oUbeHoYFQs6O4qbvKQheKmV7NeXJOLJZia_kZtP0_2GuKR0V9zsSeLEwGslM7AVyNYIgqHT6PS9IOdFWEj__Ro4sSV8PiF8kcOUdwdGI7z34TmQRD3k_XiBV9HELNkKXdG2mVu3m8FoFXEylxfWVT6_3Fz35HqhXQtNSVkFc7OtZOA5b38J7WB7Sr5kpB206BLFi2oEQU6Et6xl-UJThUYBITzN2GHMEB-IJQeW0wJJLEO2L4teIOIghJIdpHXhgsoWRi6QQuozKLEXUvg6nLA6Vx8NCb4WYsHznxDknGZyZD6HaaHuO4xQ0c2pQbdxRv8ltQ="

# ====== CLIENTS ======

user = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    device_model="Hybrid-Leech",
    system_version="FastMode",
    app_version="1.0",
    flood_sleep_threshold=0
)

bot = TelegramClient(
    "bot",
    API_ID,
    API_HASH
)

# ====== MAIN ======

async def main():
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)

    me = await user.get_me()
    print(f"✅ USER READY: {me.first_name}")
    print("🚀 SPEED MODE ENABLED (TERMUX)")
    print("🤖 BOT + USER HYBRID RUNNING")

    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
