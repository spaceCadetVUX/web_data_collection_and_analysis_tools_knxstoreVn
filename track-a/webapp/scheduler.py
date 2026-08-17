"""APScheduler nội bộ — thay Schedule Trigger của n8n. Chạy trong cùng process với FastAPI
app (uvicorn), nên chỉ hoạt động khi webapp đang chạy — xem README/A5 note về giới hạn này.
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db import get_conn

_scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
_JOB_ID = "weekly_registry_diff"
_JOB_ID_CONTENT = "daily_content_fetch"

# APScheduler day_of_week: 0=Monday .. 6=Sunday — khớp quy ước schedule_weekday trong DB
_WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _run_scheduled_job():
    from pipeline import run_full_pipeline
    run_full_pipeline(trigger_type="scheduled")


def _run_scheduled_content_job():
    from content_pipeline import run_content_pipeline
    run_content_pipeline(mode="latest")


def _load_schedule() -> tuple[int, int, int]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT schedule_weekday, schedule_hour, schedule_minute FROM registry.app_settings WHERE id = 1")
        row = cur.fetchone()
        return row["schedule_weekday"], row["schedule_hour"], row["schedule_minute"]


def _load_content_schedule() -> tuple[bool, str, int, int, int]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT schedule_enabled, schedule_frequency, schedule_weekday, schedule_hour, schedule_minute "
            "FROM news.content_settings WHERE id = 1"
        )
        row = cur.fetchone()
        return (
            row["schedule_enabled"], row["schedule_frequency"], row["schedule_weekday"],
            row["schedule_hour"], row["schedule_minute"],
        )


def reschedule():
    weekday, hour, minute = _load_schedule()
    trigger = CronTrigger(day_of_week=_WEEKDAY_NAMES[weekday], hour=hour, minute=minute)
    if _scheduler.get_job(_JOB_ID):
        _scheduler.reschedule_job(_JOB_ID, trigger=trigger)
    else:
        _scheduler.add_job(_run_scheduled_job, trigger=trigger, id=_JOB_ID)


def reschedule_content():
    """Lịch cho Track B (luôn chạy mode='latest') — khác reschedule() ở trên: có cờ
    schedule_enabled (mặc định tắt) vì đây là tính năng mới, không phải lịch nào cũng bật sẵn
    như weekly_registry_diff. Xoá job cũ rồi thêm lại nếu enabled, đơn giản hơn tìm API
    pause/resume của APScheduler mà vẫn đúng ý nghĩa (tắt = không job nào trong scheduler).
    schedule_frequency chọn được 'daily' (chỉ giờ:phút) hoặc 'weekly' (thêm weekday, tái dùng
    _WEEKDAY_NAMES/quy ước 0=Monday giống reschedule())."""
    enabled, frequency, weekday, hour, minute = _load_content_schedule()
    if _scheduler.get_job(_JOB_ID_CONTENT):
        _scheduler.remove_job(_JOB_ID_CONTENT)
    if enabled:
        if frequency == "weekly":
            trigger = CronTrigger(day_of_week=_WEEKDAY_NAMES[weekday], hour=hour, minute=minute)
        else:
            trigger = CronTrigger(hour=hour, minute=minute)
        _scheduler.add_job(_run_scheduled_content_job, trigger=trigger, id=_JOB_ID_CONTENT)


def start():
    reschedule()
    reschedule_content()
    if not _scheduler.running:
        _scheduler.start()
