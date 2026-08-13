"""Toàn bộ pipeline Track A: crawl KNX+Matter -> import Postgres -> query diff -> format
message -> gửi Zalo. Thay thế node n8n cũ (query diff + format + gửi) VÀ script
run_weekly_crawl.sh (crawl + import) — gộp lại 1 chỗ để Settings/Trigger đều điều khiển
được từ webapp, không cần đụng launchd nữa.
"""
from __future__ import annotations

import re
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


# Parse đúng nguyên văn dòng print trong crawl_knx_devices.py / crawl_matter_devices.py —
# xem grep "print(" 2 file đó nếu sửa lại format, phải sửa regex ở đây theo.
_RE_KNX_TOTAL = re.compile(r"Tổng (\d+) thiết bị, ước tính (\d+) trang\.")
_RE_KNX_PROGRESS = re.compile(r"Trang \d+: \+\d+ thiết bị \(tổng đã crawl: (\d+)\)")
_RE_MATTER_VENDORS = re.compile(r"Đã lấy (\d+) vendor\.")
_RE_MATTER_MODELS = re.compile(r"Đã lấy (\d+) model\.")


def _set_progress(progress: dict | None, **kwargs):
    if progress is not None:
        progress.update(kwargs)


def _run_tracked(
    cmd: list[str], process_registry: dict | None, on_line=None
) -> subprocess.CompletedProcess:
    """subprocess.run tương đương, nhưng đọc stdout từng dòng ngay khi có (để on_line cập nhật
    progress real-time) và lưu Popen vào process_registry để /stop terminate được giữa lúc
    đang chạy (chủ yếu dùng cho crawl KNX — mất 15-20 phút)."""
    proc = subprocess.Popen(
        cmd, cwd=str(SRC_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    if process_registry is not None:
        process_registry["proc"] = proc

    lines = []
    for line in proc.stdout:
        lines.append(line)
        if on_line is not None:
            on_line(line)
    proc.wait()
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout="".join(lines))


def _run_crawl_and_import(
    registry_key: str,
    crawl_script: str,
    csv_name: str,
    process_registry: dict | None = None,
    progress: dict | None = None,
) -> tuple[bool, str]:
    """Chạy crawler + import_and_diff.py cho 1 registry_key. Trả về (ok, log_text)."""
    csv_path = DATA_DIR / csv_name
    log = []
    label = REGISTRY_LABELS.get(registry_key, registry_key)

    def _on_crawl_line(line: str):
        if m := _RE_KNX_TOTAL.search(line):
            _set_progress(progress, phase=f"Crawl {label}", current=0, total=int(m.group(1)), percent=0)
        elif m := _RE_KNX_PROGRESS.search(line):
            current = int(m.group(1))
            total = progress.get("total") if progress else None
            percent = round(current / total * 100, 1) if total else None
            _set_progress(progress, phase=f"Crawl {label}", current=current, total=total, percent=percent)
        elif m := _RE_MATTER_VENDORS.search(line):
            _set_progress(progress, phase=f"Crawl {label} — vendor", current=int(m.group(1)), total=None, percent=None)
        elif m := _RE_MATTER_MODELS.search(line):
            _set_progress(progress, phase=f"Crawl {label} — model", current=int(m.group(1)), total=None, percent=None)

    _set_progress(progress, phase=f"Crawl {label}", current=0, total=None, percent=None)
    crawl = _run_tracked(
        [sys.executable, str(SRC_DIR / crawl_script), "--output", str(csv_path)],
        process_registry, on_line=_on_crawl_line,
    )
    log.append(f"--- {registry_key} crawl ---\n{crawl.stdout}")
    if crawl.returncode != 0:
        return False, "\n".join(log)

    _set_progress(progress, phase=f"Import {label} vào Postgres", current=None, total=None, percent=None)
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
    trigger_type: str = "manual",
    stop_event=None,
    process_registry: dict | None = None,
    progress: dict | None = None,
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
        "knx", "crawl_knx_devices.py", "_weekly_knx.csv", process_registry, progress
    )
    crawl_logs.append(knx_log)

    if stop_event is not None and stop_event.is_set():
        stopped, matter_ok = True, False
    else:
        matter_ok, matter_log = _run_crawl_and_import(
            "matter_csa", "crawl_matter_devices.py", "_weekly_matter.csv", process_registry, progress
        )
        crawl_logs.append(matter_log)
        if stop_event is not None and stop_event.is_set():
            stopped = True

    device_count, devices, message = None, None, None
    send_ok, send_error = False, None

    if stopped:
        send_error = "stopped_by_user"
    elif knx_ok and matter_ok:
        _set_progress(progress, phase="Tính diff", current=None, total=None, percent=None)
        device_count, devices = query_diff()
        message = format_message(device_count, devices)
        _set_progress(progress, phase="Gửi Zalo", current=None, total=None, percent=None)
        send_ok, send_error = send_to_khub(message)
    else:
        send_error = "crawl_or_import_failed"

    _set_progress(progress, phase="Hoàn tất", current=None, total=None, percent=100)

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
