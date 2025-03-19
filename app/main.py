import asyncio
import logging.config

from bot.uzum_bot import bot, dp
from db.client import sessionmanager
from config.logging import LOGGING
from config.settings import app_config


logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


async def on_startup(dispatcher):
    sessionmanager.init(app_config.database_uri)


async def on_shutdown(dispatcher):
    await sessionmanager.close()


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
