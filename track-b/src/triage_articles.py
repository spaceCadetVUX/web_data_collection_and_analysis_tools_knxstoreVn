#!/usr/bin/env python3
"""
B3 — Triage tầng 1 cho Track B (news pipeline). Đọc bài chưa triage từ news.articles, gọi
Claude qua CLI `claude -p` (dùng subscription Claude Code có sẵn — quyết định 2026-08-15,
KHÔNG dùng Anthropic Messages/Batch API tính phí token riêng), ghi verdict vào news.analysis.

Vì sao gộp batch: mỗi lần gọi `claude -p` tốn phí cố định do harness tự nạp skill/tool/memory
list (~$0.02-0.04/lần dù câu hỏi ngắn) — gộp N bài/lần amortize chi phí này. Test thật
2026-08-15: 1 bài/lần = $0.0408, 3 bài/lần = $0.0183 (rẻ hơn ~55%/bài). Batch mặc định 15.

Vì sao chạy từ thư mục trung lập (--tmp-cwd): gọi claude -p TỪ TRONG project này sẽ tự nạp
thêm CLAUDE.md/AGENTS.md do GitNexus sinh ra (~7.700 token thêm/lần, đã verify thật) — không
liên quan gì tới việc phân loại bài viết, thuần lãng phí.

Schema output theo đúng docs/plan.md §6.1 (verdict/topics/brands/content_type/confidence) —
KHÔNG hỏi summary_vi/why_it_matters/recommended_action ở đây, đó là việc "deep analysis"
(§6.3), chạy trên EVENT sau khi clustering (B4), không phải trên từng article riêng lẻ.

Cách chạy:
    python3 triage_articles.py --db-url postgresql://user:pass@host:port/db
    python3 triage_articles.py --db-url ... --limit 15   # test 1 batch nhỏ
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile

import psycopg2
import psycopg2.extras

MODEL = "claude-haiku-4-5"
MAX_BODY_WORDS = 1200  # xem docs/plan.md §6.1 — chỉ cần title + 1200 từ đầu, không cả bài

CONTENT_TYPE_ENUM = ("product_release", "standard_update", "recall", "eol", "acquisition",
                     "price_change", "tender", "case_study", "opinion", "other")
VERDICT_ENUM = ("ignore", "archive", "digest", "alert")
CONFIDENCE_ENUM = ("low", "medium", "high")


def _truncate_body(body_text: str, max_words: int = MAX_BODY_WORDS) -> str:
    words = body_text.split()
    return " ".join(words[:max_words])


def _build_prompt(batch: list[dict], brands_of_interest: list[str]) -> str:
    articles_block = []
    for i, art in enumerate(batch):
        excerpt = _truncate_body(art["body_text"] or "")
        articles_block.append(
            f"### Bài {i}\nNguồn: {art['source_name']}\nTiêu đề: {art['title']}\n"
            f"Nội dung (trích): {excerpt}\n"
        )

    return f"""Bạn là bộ lọc triage cho hệ thống theo dõi tin tức building automation (KNX,
DALI, Matter, BACnet, Modbus) của 1 nhà phân phối tại Việt Nam.

Danh sách brand đang quan tâm: {", ".join(brands_of_interest)}

Với MỖI bài dưới đây, trả về 1 object JSON:
{{
  "index": <số thứ tự bài, khớp "Bài N" ở trên>,
  "verdict": "ignore" | "archive" | "digest" | "alert",
  "topics": [<danh sách chủ đề ngắn, vd "KNX", "lighting_control">],
  "brands": [<brand nào trong bài THUỘC danh sách quan tâm ở trên, rỗng nếu không có>],
  "content_type": "product_release" | "standard_update" | "recall" | "eol" | "acquisition" | "price_change" | "tender" | "case_study" | "opinion" | "other",
  "confidence": "low" | "medium" | "high"
}}

Quy tắc verdict:
- "alert": brand thuộc danh sách quan tâm VÀ content_type thuộc {{recall, eol, standard_update}}.
- "digest": liên quan trực tiếp tới building automation, đáng đọc nhưng không khẩn cấp.
- "archive": có liên quan xa nhưng không đáng đưa vào digest hàng ngày.
- "ignore": không liên quan gì tới building automation.

Trả về DUY NHẤT 1 JSON array chứa đúng {len(batch)} object (1 object/bài), không giải thích
gì thêm, không dùng markdown code fence.

{"".join(articles_block)}"""


def _parse_claude_json_envelope(raw_stdout: str) -> dict:
    envelope = json.loads(raw_stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude -p báo lỗi: {envelope}")
    result_text = envelope["result"]
    # Bỏ markdown code fence nếu có (```json ... ``` hoặc ``` ... ```) — claude -p không phải
    # lúc nào cũng tuân thủ "không dùng markdown" dù đã yêu cầu trong prompt.
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", result_text, re.DOTALL)
    json_text = match.group(1) if match else result_text
    verdicts = json.loads(json_text)
    return verdicts, envelope


def triage_batch(batch: list[dict], brands_of_interest: list[str]) -> tuple[list[dict], dict]:
    prompt = _build_prompt(batch, brands_of_interest)
    with tempfile.TemporaryDirectory() as tmp_cwd:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json", "--model", MODEL],
            cwd=tmp_cwd, capture_output=True, text=True, timeout=180,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p thoát với returncode {proc.returncode}: {proc.stderr[:500]}")
    verdicts, envelope = _parse_claude_json_envelope(proc.stdout)
    if not isinstance(verdicts, list):
        raise ValueError(f"Kỳ vọng JSON array, nhận: {type(verdicts)}")
    return verdicts, envelope


def _validate_verdict(v: dict) -> bool:
    return (
        v.get("verdict") in VERDICT_ENUM
        and v.get("content_type") in CONTENT_TYPE_ENUM
        and v.get("confidence") in CONFIDENCE_ENUM
        and isinstance(v.get("topics"), list)
        and isinstance(v.get("brands"), list)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--batch-size", type=int, default=15,
                         help="Số bài gộp vào 1 lần gọi claude -p (mặc định 15 — xem docstring "
                              "về lý do gộp batch để giảm chi phí cố định mỗi lần gọi)")
    parser.add_argument("--limit", type=int, default=None,
                         help="Giới hạn tổng số bài xử lý (test), mặc định xử lý hết bài chưa triage")
    args = parser.parse_args()

    conn = psycopg2.connect(args.db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT brand FROM registry.brands_of_interest WHERE is_active ORDER BY brand")
    brands_of_interest = [r["brand"] for r in cur.fetchall()]

    cur.execute(
        """
        SELECT a.id, a.title, a.body_text, s.name AS source_name
        FROM news.articles a
        JOIN news.sources s ON s.id = a.source_id
        LEFT JOIN news.analysis an ON an.article_id = a.id AND an.stage = 'triage'
        WHERE an.id IS NULL AND a.extract_status = 'ok'
        ORDER BY a.first_seen_at DESC
        """
    )
    pending = cur.fetchall()
    if args.limit:
        pending = pending[: args.limit]

    if not pending:
        print("Không có bài nào chờ triage.")
        conn.close()
        return

    print(f"Có {len(pending)} bài chờ triage, batch {args.batch_size} bài/lần "
          f"({-(-len(pending) // args.batch_size)} lần gọi claude -p).")

    total_cost = 0.0
    done, failed = 0, 0
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start:start + args.batch_size]
        try:
            verdicts, envelope = triage_batch(batch, brands_of_interest)
            cost = envelope.get("total_cost_usd", 0) or 0
            total_cost += cost
            print(f"Batch {start // args.batch_size + 1}: {len(batch)} bài, chi phí ${cost:.4f}")

            by_index = {v.get("index"): v for v in verdicts if isinstance(v, dict)}
            for i, art in enumerate(batch):
                v = by_index.get(i)
                if v is None or not _validate_verdict(v):
                    print(f"  LỖI: bài {i} ({art['title']!r}) không có verdict hợp lệ, bỏ qua", file=sys.stderr)
                    failed += 1
                    continue
                cur.execute(
                    """
                    INSERT INTO news.analysis
                        (article_id, stage, model, route, verdict, topics, brands,
                         content_type, confidence, raw_response)
                    VALUES (%s, 'triage', %s, 'realtime', %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (art["id"], MODEL, v["verdict"], v["topics"], v["brands"],
                     v["content_type"], v["confidence"], json.dumps(envelope)),
                )
                done += 1
            conn.commit()
        except Exception as exc:  # noqa: BLE001 — 1 batch lỗi không được kéo sập cả lần chạy
            conn.rollback()
            print(f"LỖI batch bắt đầu từ bài {start}: {exc}", file=sys.stderr)
            failed += len(batch)

    print(f"Xong: {done} bài triage thành công, {failed} lỗi/bỏ qua, tổng chi phí ${total_cost:.4f}")
    conn.close()


if __name__ == "__main__":
    main()
