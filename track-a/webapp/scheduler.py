"""APScheduler nội bộ — thay Schedule Trigger của n8n. Chạy trong cùng process với FastAPI
app (uvicorn), nên chỉ hoạt động khi webapp đang chạy — xem README/A5 note về giới hạn này.
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db import get_conn

_scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
_JOB_ID = "weekly_registry_diff"

# APScheduler day_of_week: 0=Monday .. 6=Sunday — khớp quy ước schedule_weekday trong DB
_WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _run_scheduled_job():
    from pipeline import run_full_pipeline
    run_full_pipeline(trigger_type="scheduled")


def _load_schedule() -> tuple[int, int, int]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT schedule_weekday, schedule_hour, schedule_minute FROM registry.app_settings WHERE id = 1")
        row = cur.fetchone()
        return row["schedule_weekday"], row["schedule_hour"], row["schedule_minute"]


def reschedule():
    weekday, hour, minute = _load_schedule()
    trigger = CronTrigger(day_of_week=_WEEKDAY_NAMES[weekday], hour=hour, minute=minute)
    if _scheduler.get_job(_JOB_ID):
        _scheduler.reschedule_job(_JOB_ID, trigger=trigger)
    else:
        _scheduler.add_job(_run_scheduled_job, trigger=trigger, id=_JOB_ID)


def start():
    reschedule()
    if not _scheduler.running:
        _scheduler.start()
