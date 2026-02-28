"""
stocks-refdata: scheduler runs instruments + fundamentals at midnight; optional run on startup.
"""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from refdata_job import run_job

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    run_on_start = os.environ.get("REFDATA_RUN_ON_START", "0").lower() in ("1", "true", "yes")
    if run_on_start:
        logger.info("Running refdata job once on startup")
        run_job()

    scheduler = BlockingScheduler()
    scheduler.add_job(run_job, CronTrigger(hour=0, minute=0), id="refdata")
    logger.info("Scheduler: refdata at midnight UTC")
    scheduler.start()


if __name__ == "__main__":
    main()
