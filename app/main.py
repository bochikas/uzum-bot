import asyncio
from logging import config as logging_config
from logging import getLogger

from bot.uzum_bot import UzumBot
from config.logging import LOGGING

logging_config.dictConfig(LOGGING)
logger = getLogger(__name__)


async def main():
    bot = UzumBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
