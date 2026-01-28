import os

def get_env(name, cast=str, required=True):
    value = os.getenv(name)
    if value is None:
        if required:
            raise RuntimeError(f"❌ ENV variable missing: {name}")
        return None
    try:
        return cast(value)
    except Exception:
        raise RuntimeError(f"❌ ENV variable invalid type: {name}")

API_ID = get_env("API_ID", int)
API_HASH = get_env("API_HASH", str)
BOT_TOKEN = get_env("BOT_TOKEN", str)
