import asyncio

from aiogram import Bot

from backend.config import BOT_TOKEN
from backend.database import db
from bot.handlers import register_handlers, dp  # <-- import dp from handlers
from bot.middlewares import ThrottlingMiddleware


async def main():
    bot = Bot(token=BOT_TOKEN)

    # Register throttling middleware
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.5))

    register_handlers(dp)

    if db.is_empty():
        db.import_from_csv()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())