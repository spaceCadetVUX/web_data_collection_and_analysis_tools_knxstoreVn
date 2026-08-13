"""Toàn bộ pipeline Track A: crawl KNX+Matter -> import Postgres -> query diff -> format
message -> gửi Zalo. Thay thế node n8n cũ (query diff + format + gửi) VÀ script
run_weekly_crawl.sh (crawl + import) — gộp lại 1 chỗ để Settings/Trigger đều điều khiển
được từ webapp, không cần đụng launchd nữa.
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from db import DB_URL, get_conn
from zalo import send_to_khub

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REGISTRY_LABELS = {"knx": "KNX", "matter_csa": "CSA Matter", "dali": "DALI"}

DIFF_QUERY = """
SELECT count(*) AS device_count, coalesce(json_agg(row_to_json(t)), '[]'::json) AS devices
FROM (
  SELECT d.registry_key, d.external_id, d.brand, d.model, d.first_seen_at
  FROM registry.devices d
  JOIN registry.brands_of_interest b
    ON b.is_active
   AND (
        lower(d.brand) = lower(b.brand)
        OR lower(d.brand) = ANY (SELECT lower(a) FROM unnest(b.aliases) a)
       )
  JOIN LATERAL (
    SELECT run_at FROM registry.crawl_log cl
    WHERE cl.registry_key = d.registry_key AND cl.status = 'ok'
    ORDER BY run_at DESC LIMIT 1
  ) latest_run ON true
  WHERE d.status = 'active'
    AND d.first_seen_at >= latest_run.run_at
) t;
"""


def _run_tracked(cmd: list[str], process_registry: dict | None) -> subprocess.CompletedProcess:
    """subprocess.run tương đương, nhưng lưu Popen vào process_registry để /stop terminate được
    giữa lúc đang chạy (chủ yếu dùng cho crawl KNX — mất 15-20 phút)."""
    proc = subprocess.Popen(
        cmd, cwd=str(SRC_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    if process_registry is not None:
        process_registry["proc"] = proc
    stdout, _ = proc.communicate()
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout=stdout)


def _run_crawl_and_import(
    registry_key: str, crawl_script: str, csv_name: str, process_registry: dict | None = None
) -> tuple[bool, str]:
    """Chạy crawler + import_and_diff.py cho 1 registry_key. Trả về (ok, log_text)."""
    csv_path = DATA_DIR / csv_name
    log = []

    crawl = _run_tracked(
        [sys.executable, str(SRC_DIR / crawl_script), "--output", str(csv_path)], process_registry
    )
    log.append(f"--- {registry_key} crawl ---\n{crawl.stdout}")
    if crawl.returncode != 0:
        return False, "\n".join(log)

    imp = _run_tracked(
        [
            sys.executable, str(SRC_DIR / "import_and_diff.py"),
            "--db-url", DB_URL, "--csv", str(csv_path), "--registry-key", registry_key,
        ],
        process_registry,
    )
    log.append(f"--- {registry_key} import ---\n{imp.stdout}")
    return imp.returncode == 0, "\n".join(log)


def query_diff() -> tuple[int, list[dict]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(DIFF_QUERY)
        row = cur.fetchone()
        return row["device_count"], row["devices"]


def format_message(device_count: int, devices: list[dict]) -> str:
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    fmt = lambda d: d.strftime("%d/%m/%Y")

    if device_count == 0:
        return (
            f"📭 Registry Diff — tuần {fmt(week_ago)} đến {fmt(now)}\n\n"
            "Không có thiết bị mới nào khớp brand quan tâm tuần này."
        )

    by_registry: dict[str, list[dict]] = {}
    for d in devices:
        by_registry.setdefault(d["registry_key"], []).append(d)

    lines = [f"🔔 Registry Diff — tuần {fmt(week_ago)} đến {fmt(now)}", ""]
    for key, items in by_registry.items():
        label = REGISTRY_LABELS.get(key, key)
        lines.append(f"{label} ({len(items)} thiết bị mới):")
        for d in items:
            cert_date = datetime.fromisoformat(str(d["first_seen_at"])).strftime("%d/%m/%Y")
            lines.append(f"• {d['brand']} — {d['model']} — cert {cert_date}")
        lines.append("")
    return "\n".join(lines).strip()


def run_full_pipeline(
    trigger_type: str = "manual", stop_event=None, process_registry: dict | None = None
) -> dict:
    """Chạy toàn bộ: crawl + import (KNX, Matter) -> query diff -> format -> gửi Zalo.
    Luôn ghi 1 dòng vào registry.digest_log, kể cả khi crawl fail hoặc bị dừng tay — không
    để "chết âm thầm". stop_event (threading.Event) cho phép /stop ngắt giữa các bước; nếu
    ngắt ngay giữa lúc crawl đang chạy, process_registry["proc"].terminate() làm crawl thoát
    sớm (return code != 0), _run_crawl_and_import trả về False như crawl fail bình thường.
    """
    started = time.monotonic()
    crawl_logs = []
    stopped = False

    knx_ok, knx_log = _run_crawl_and_import(
        "knx", "crawl_knx_devices.py", "_weekly_knx.csv", process_registry
    )
    crawl_logs.append(knx_log)

    if stop_event is not None and stop_event.is_set():
        stopped, matter_ok = True, False
    else:
        matter_ok, matter_log = _run_crawl_and_import(
            "matter_csa", "crawl_matter_devices.py", "_weekly_matter.csv", process_registry
        )
        crawl_logs.append(matter_log)
        if stop_event is not None and stop_event.is_set():
            stopped = True

    device_count, devices, message = None, None, None
    send_ok, send_error = False, None

    if stopped:
        send_error = "stopped_by_user"
    elif knx_ok and matter_ok:
        device_count, devices = query_diff()
        message = format_message(device_count, devices)
        send_ok, send_error = send_to_khub(message)
    else:
        send_error = "crawl_or_import_failed"

    duration_ms = int((time.monotonic() - started) * 1000)
    status = "ok" if send_ok else ("failed" if send_error != "skipped_no_credential" else "skipped_no_credential")

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO registry.digest_log
                (trigger_type, device_count, message, send_status, error, duration_ms)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (trigger_type, device_count, message, status, send_error, duration_ms),
        )
        conn.commit()

    return {
        "knx_ok": knx_ok,
        "matter_ok": matter_ok,
        "stopped": stopped,
        "device_count": device_count,
        "message": message,
        "send_status": status,
        "duration_ms": duration_ms,
        "crawl_log_text": "\n\n".join(crawl_logs),
    }


if __name__ == "__main__":
    result = run_full_pipeline(trigger_type="manual")
    print(f"knx_ok={result['knx_ok']} matter_ok={result['matter_ok']} "
          f"device_count={result['device_count']} send_status={result['send_status']} "
          f"duration_ms={result['duration_ms']}")
    if result["message"]:
        print("--- message ---")
        print(result["message"])
