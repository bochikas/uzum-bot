import asyncio
from logging import config as logging_config
from logging import getLogger

from app.bot.uzum_bot import UzumBot
from app.config.logging import LOGGING
from app.config.settings import app_config
from app.db.client import sessionmanager

logging_config.dictConfig(LOGGING)
logger = getLogger(__name__)


async def main():
    try:
        sessionmanager.init(app_config.database_uri)
        bot = UzumBot()
        await bot.run()
    finally:
        await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
