"""
refdata: scheduler runs instruments + fundamentals at midnight; optional run on startup.
"""
import logging
import os
import sys
from pathlib import Path

# When running/debugging this file directly, the repo root isn't always on sys.path.
# Ensure we can import top-level modules like `app_logging`.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REFDATA_DIR = Path(__file__).resolve().parent
if str(REFDATA_DIR) not in sys.path:
    sys.path.insert(0, str(REFDATA_DIR))



from app_logging import setup_logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from refdata_job import run_job

setup_logging("refdata")
logger = logging.getLogger(__name__)

runNow = True # Run the job immediately. Only set to True for testing.

def main():
    run_on_start = os.environ.get("REFDATA_RUN_ON_START", "0").lower() in ("1", "true", "yes")
    if run_on_start:
        logger.info("Running refdata job once on startup")
        run_job()

    if runNow:
        logger.info("Running refdata job immediately")
        run_job()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(run_job, CronTrigger(hour=0, minute=0), id="refdata")
    logger.info("Scheduler: refdata at midnight UTC")
    scheduler.start()


if __name__ == "__main__":
    main()
