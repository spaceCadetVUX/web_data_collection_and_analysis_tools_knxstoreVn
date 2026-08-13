"""Gửi tin nhắn qua Zalo KHub.

Chưa có credential/API thật của KHub trong môi trường dev này (xem
track-a/A5-n8n-workflow.md mục "Việc chưa giải quyết" — docs/plan.md ghi delivery là
"Zalo KHub MCP", orchestrator production ở n8n.tungvu.vn, khác máy này).

Khi có API key/endpoint KHub thật: điền vào đây, không cần sửa gì ở pipeline.py.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PLACEHOLDER_LOG = Path(__file__).resolve().parent / "khub_placeholder_log.jsonl"


def send_to_khub(message: str) -> tuple[bool, str | None]:
    """Trả về (success, error). Hiện tại luôn ghi placeholder, không gửi thật."""
    entry = {"sent_at": datetime.now().isoformat(), "message": message}
    with open(PLACEHOLDER_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return False, "skipped_no_credential"
