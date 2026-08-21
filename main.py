import asyncio
import os

from aiohttp import web
from aiogram import Bot
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from backend.config import BOT_TOKEN
from backend.database import db
from bot.handlers import register_handlers, dp
from bot.middlewares import ThrottlingMiddleware

# ── Config ───────────────────────────────────────────────────────────
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 8080))

# Render auto-sets this. Empty string = local dev (falls back to polling)
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"


# ── Startup / Shutdown ───────────────────────────────────────────────
async def on_startup(bot: Bot):
    if db.is_empty():
        db.import_from_csv()
    if WEBHOOK_HOST:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook set: {WEBHOOK_URL}")
    else:
        print("🖥️  Local mode — no webhook")


async def on_shutdown(bot: Bot):
    if WEBHOOK_HOST:
        await bot.delete_webhook()
        print("🛑 Webhook deleted")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    bot = Bot(token=BOT_TOKEN)

    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.5))
