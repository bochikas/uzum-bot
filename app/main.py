import asyncio
from logging import config as logging_config
from logging import getLogger

from bot.uzum_bot import UzumBot
from config.logging import LOGGING
from scheduler.scheduler import Scheduler

logging_config.dictConfig(LOGGING)
logger = getLogger(__name__)


async def main():
    bot = UzumBot(Scheduler)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
