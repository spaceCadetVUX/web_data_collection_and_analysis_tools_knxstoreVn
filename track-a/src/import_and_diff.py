#!/usr/bin/env python3
"""
Import 1 lần crawl (CSV từ crawl_knx_devices.py / crawl_matter_devices.py) vào
registry.devices, chạy đúng logic "Hành vi mong muốn" ở A2-knx-crawler.md:
UPSERT + anomaly check + ghi registry.snapshots/registry.crawl_log.

Generic cho mọi registry_key (knx, matter_csa, dali...) — chỉ cần CSV có tối thiểu
3 cột: external_id, brand, model. Cột nào khác (source_url, device_type_id...) tự
động gom vào cột attributes (jsonb), không cần khai báo riêng cho từng nguồn.

Cách chạy:
    python3 import_and_diff.py --db-url postgresql://user:pass@host:5432/db \
        --csv matter_devices_baseline.csv --registry-key matter_csa
"""

import argparse
import csv
import json
import sys

import psycopg2

CORE_FIELDS = ("external_id", "brand", "model")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-url", required=True, help="postgresql://user:pass@host:port/db")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--registry-key", required=True, help="knx | matter_csa | dali")
    parser.add_argument("--anomaly-threshold", type=float, default=0.8,
                         help="Abort nếu item_count lần này < threshold * avg các lần 'ok' trước (mặc định 0.8 = giảm hơn 20%%)")
    parser.add_argument("--incremental", action="store_true",
                         help="CSV chỉ chứa 1 phần registry (crawl mới nhất, dừng sớm khi gặp "
                              "thiết bị đã biết — xem crawl_knx_devices.py --known-ids-file). "
                              "Bỏ qua anomaly-check (baseline so sánh là full crawl, không áp "
                              "dụng cho tập con) và KHÔNG đánh dấu removed cho thiết bị vắng mặt "
                              "trong CSV (vì phần lớn registry không nằm trong lần crawl này, "
                              "đánh dấu removed sẽ sai gần như toàn bộ registry.devices).")
    args = parser.parse_args()

    with open(args.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    item_count = len(rows)

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False
    cur = conn.cursor()
    # now() Postgres = cố định theo thời điểm bắt đầu transaction, dùng cho mốc diff
    # (first_seen_at DEFAULT now() của các row insert trong transaction này cũng ra
    # đúng giá trị này) — không dùng đồng hồ máy chạy script vì lệch giờ giữa container
    # script (n8n) và container Postgres, dù chỉ vài ms, sẽ làm sai query diff.
    # clock_timestamp() = giờ thực tại thời điểm gọi, dùng riêng để đo duration_ms.
    cur.execute("SELECT now(), clock_timestamp()")
    start, wall_start = cur.fetchone()

    crawl_mode = "incremental" if args.incremental else "full"

    if item_count == 0:
        # Ghi crawl_log.status='failed' trước khi thoát — nếu không, case này biến mất
        # hoàn toàn khỏi crawl_log (khác case aborted_anomaly có ghi), đúng loại "chết âm
        # thầm" mà bảng crawl_log được tạo ra để tránh (xem A2-knx-crawler.md).
        cur.execute(
            """INSERT INTO registry.crawl_log (registry_key, run_at, item_count, status, error, crawl_mode)
               VALUES (%s, %s, 0, 'failed', %s, %s)""",
            (args.registry_key, start, "CSV rỗng — có thể crawler bị lỗi hoặc nguồn tạm không trả kết quả", crawl_mode),
        )
        conn.commit()
        print("CSV rỗng, không làm gì cả — có thể crawler bị lỗi, kiểm tra lại trước khi chạy. "
              "Đã ghi crawl_log.status=failed.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.incremental:
            avg_count = None  # anomaly-check không áp dụng — xem docstring --incremental
        else:
            # Chỉ so với các lần full crawl trước — trộn chung incremental (vài chục item)
            # vào average sẽ làm hỏng baseline dùng để phát hiện anomaly cho full crawl.
            cur.execute(
                "SELECT avg(item_count) FROM registry.crawl_log "
                "WHERE registry_key = %s AND status = 'ok' AND crawl_mode = 'full'",
                (args.registry_key,),
            )
            avg_count = cur.fetchone()[0]

        if avg_count is not None and item_count < float(avg_count) * args.anomaly_threshold:
            cur.execute(
                """INSERT INTO registry.crawl_log (registry_key, run_at, item_count, status, error, crawl_mode)
                   VALUES (%s, %s, %s, 'aborted_anomaly', %s, %s)""",
                (args.registry_key, start, item_count,
                 f"item_count={item_count} < {args.anomaly_threshold}*avg({avg_count})", crawl_mode),
            )
            conn.commit()
            print(f"ANOMALY: item_count={item_count} thấp bất thường so với avg trước "
                  f"đó ({avg_count}). Không update registry.devices, không mark removed. "
                  f"Đã ghi crawl_log.status=aborted_anomaly — cần người kiểm tra thủ công.")
            return

        seen_ids = []
        new_count = 0
        for row in rows:
            row = dict(row)
            ext_id = row.pop("external_id")
            brand = row.pop("brand")
            model = row.pop("model")
            attributes = json.dumps(row)
            seen_ids.append(ext_id)

            cur.execute(
                """INSERT INTO registry.devices (registry_key, external_id, brand, model, attributes)
                   VALUES (%s, %s, %s, %s, %s::jsonb)
                   ON CONFLICT (registry_key, external_id) DO UPDATE
                     SET last_seen_at = now(), brand = EXCLUDED.brand,
                         model = EXCLUDED.model, attributes = EXCLUDED.attributes,
                         status = 'active'
                   RETURNING (xmax = 0) AS is_new""",
                (args.registry_key, ext_id, brand, model, attributes),
            )
            if cur.fetchone()[0]:
                new_count += 1

        if args.incremental:
            # Không đánh dấu removed — CSV chỉ chứa 1 phần registry (xem docstring --incremental),
            # phần lớn thiết bị active thật sự không nằm trong seen_ids của lần crawl này.
            removed_count = 0
        else:
            cur.execute(
                """UPDATE registry.devices SET status = 'removed'
                   WHERE registry_key = %s AND status = 'active' AND NOT (external_id = ANY(%s))
                   RETURNING external_id""",
                (args.registry_key, seen_ids),
            )
            removed_count = len(cur.fetchall())

        if not args.incremental:
            # snapshots dùng để theo dõi item_count toàn registry theo thời gian — incremental
            # chỉ crawl 1 phần nhỏ, ghi vào đây sẽ làm sai biểu đồ/lịch sử item_count thật.
            cur.execute(
                """INSERT INTO registry.snapshots (registry_key, taken_at, item_count, raw)
                   VALUES (%s, %s, %s, %s::jsonb)""",
                (args.registry_key, start, item_count, json.dumps({"source_csv": args.csv})),
            )

        cur.execute("SELECT clock_timestamp()")
        wall_end = cur.fetchone()[0]
        duration_ms = int((wall_end - wall_start).total_seconds() * 1000)
        cur.execute(
            """INSERT INTO registry.crawl_log
                 (registry_key, run_at, item_count, new_count, removed_count, status, duration_ms, crawl_mode)
               VALUES (%s, %s, %s, %s, %s, 'ok', %s, %s)""",
            (args.registry_key, start, item_count, new_count, removed_count, duration_ms, crawl_mode),
        )

        conn.commit()
        print(f"OK: item_count={item_count}, new_count={new_count}, removed_count={removed_count}, "
              f"duration_ms={duration_ms}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
