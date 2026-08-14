"""Wrapper gọi track-b/src/extract_articles.py từ webapp — Track B (crawl blog/content),
tách biệt hoàn toàn khỏi pipeline.py (Track A, crawl sản phẩm KNX/Matter). File này chỉ lo
subprocess + progress tracking cho UI; thuật toán crawl thật nằm ở track-b/src/.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from db import DB_URL

TRACK_B_SRC = Path(__file__).resolve().parent.parent.parent / "track-b" / "src"

_MAX_LOG_LINES = 500

# mode 'full': quét backlog mỗi nguồn (cap cao — vẫn giới hạn để không chạy vô hạn nếu 1
# nguồn có nghìn bài lịch sử). mode 'latest': chỉ lấy vài bài mới nhất mỗi nguồn, nhanh —
# giống cặp "Crawl toàn bộ" / "Crawl mới nhất" bên Track A.
_MAX_NEW_PER_SOURCE = {"full": 1000, "latest": 3}


def _append_log(progress: dict | None, line: str):
    if progress is None:
        return
    log = progress.setdefault("log", [])
    log.append(line.rstrip("\n"))
    if len(log) > _MAX_LOG_LINES:
        del log[: len(log) - _MAX_LOG_LINES]


def _set_progress(progress: dict | None, **kwargs):
    if progress is not None:
        progress.update(kwargs)


def run_content_pipeline(
    mode: str,
    max_pages: int = 1,
    process_registry: dict | None = None,
    progress: dict | None = None,
) -> dict:
    """max_pages: số trang listing lật qua mỗi nguồn html_list (xem migration 0010/0011) —
    chỉ có ý nghĩa ở mode='full'; mode='latest' luôn dùng 1 (không lật trang, chỉ lấy vài
    bài mới nhất mỗi nguồn cho nhanh)."""
    if mode not in _MAX_NEW_PER_SOURCE:
        raise ValueError(f"mode phải là 'full' hoặc 'latest', nhận '{mode}'")
    max_new = _MAX_NEW_PER_SOURCE[mode]
    effective_max_pages = max_pages if mode == "full" else 1
    started = time.monotonic()

    _set_progress(progress, phase=f"Fetch content ({mode})", current=0, total=None, percent=None)
    _append_log(progress, f"=== extract_articles.py --max-new-per-source {max_new} "
                           f"--max-pages {effective_max_pages} ===")

    cmd = [
        sys.executable, "-u", str(TRACK_B_SRC / "extract_articles.py"),
        "--db-url", DB_URL, "--max-new-per-source", str(max_new),
        "--max-pages", str(effective_max_pages),
    ]
    proc = subprocess.Popen(
        cmd, cwd=str(TRACK_B_SRC), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    if process_registry is not None:
        process_registry["proc"] = proc

    new_total = 0
    for line in proc.stdout:
        _append_log(progress, line)
        if "+ Bài mới:" in line:
            new_total += 1
            _set_progress(progress, phase=f"Fetch content ({mode})", current=new_total,
                           total=None, percent=None)
    proc.wait()

    duration_ms = int((time.monotonic() - started) * 1000)
    _set_progress(progress, phase="Hoàn tất", current=new_total, total=None, percent=100)

    return {
        "ok": proc.returncode == 0,
        "mode": mode,
        "new_count": new_total,
        "duration_ms": duration_ms,
        "returncode": proc.returncode,
    }
