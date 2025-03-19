from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scheduler.jobs import fetch_product_prices


class Scheduler:
    """Планировщик задач."""

    scheduler: AsyncIOScheduler

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

        self.add_all_jobs()

    def add_all_jobs(self) -> None:
        self.scheduler.add_job(fetch_product_prices, "cron", hour="14")

    async def start(self) -> None:
        """Start."""

        self.scheduler.start()

    async def stop(self) -> None:
        """Stop."""

        self.scheduler.shutdown()
