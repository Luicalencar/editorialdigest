import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from publications.registry import list_publications, run_publication_harvest
from utils.logging import get_logger

log = get_logger(__name__)
CADENCE_HOURS = int(os.getenv("CADENCE_HOURS", "24"))
_scheduler = None

def _schedule_all(SessionLocal):
    pubs = list_publications()
    for pub in pubs:
        # stagger starts: second = index * 5
        _scheduler.add_job(
            func=lambda p=pub: run_publication_harvest(SessionLocal, p["id"]),
            trigger="interval",
            hours=CADENCE_HOURS,
            next_run_time=datetime.utcnow(),  # run once on boot
            id=f"harvest-{pub['id']}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        log.info(f"Scheduled {pub['id']} every {CADENCE_HOURS}h")

def start_scheduler(SessionLocal):
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    _schedule_all(SessionLocal)
    log.info("Scheduler started")

def trigger_publication_now(SessionLocal, publication_id: str):
    log.info(f"Manual trigger for {publication_id}")
    run_publication_harvest(SessionLocal, publication_id)

