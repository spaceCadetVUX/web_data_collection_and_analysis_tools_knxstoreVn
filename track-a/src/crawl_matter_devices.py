#!/usr/bin/env python3
"""
Crawl CSA Matter certified devices từ Distributed Compliance Ledger (DCL) -> CSV.

Khác hẳn KNX (A2): đây là REST API JSON công khai, không phải HTML scrape, không anti-bot.
Xem track-a/A4-matter-crawler.md để biết chi tiết endpoint và field mapping.

Cách chạy (test trên 1 batch nhỏ trước):
    python3 crawl_matter_devices.py --max-records 50 --output test_run.csv

Chạy full (~4.948 model, ~5-6 request, vài giây):
    python3 crawl_matter_devices.py --output matter_devices_baseline.csv
"""

import argparse
import csv
import sys
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://on.dcl.csa-iot.org"
USER_AGENT = "KNXStore-RegistryBot/1.0 (+https://knxstore.vn; internal registry diff tool)"
CSV_FIELDS = ["external_id", "brand", "model", "device_type_id", "part_number", "crawled_at"]
PAGE_LIMIT = 1000


def fetch_all_pages(session, path, item_key, delay):
    """Generic Cosmos SDK pagination: gọi tới khi pagination.next_key rỗng."""
    items = []
    next_key = None
    while True:
        params = {"pagination.limit": PAGE_LIMIT}
        if next_key:
            params["pagination.key"] = next_key
        resp = session.get(f"{BASE_URL}{path}", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get(item_key, []))
        next_key = data.get("pagination", {}).get("next_key")
        if not next_key:
            break
        time.sleep(delay)
    return items


def fetch_vendor_map(session, delay):
    vendors = fetch_all_pages(session, "/dcl/vendorinfo/vendors", "vendorInfo", delay)
    return {v["vendorID"]: v.get("vendorName", "") for v in vendors}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="matter_devices_baseline.csv", help="File CSV output")
    parser.add_argument("--max-records", type=int, default=None,
                         help="Giới hạn số model ghi ra (dùng khi test). Bỏ trống = lấy hết.")
    parser.add_argument("--delay", type=float, default=0.3, help="Giây nghỉ giữa mỗi request phân trang")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("Đang fetch vendor list...")
    try:
        vendor_map = fetch_vendor_map(session, args.delay)
    except requests.RequestException as exc:
        print(f"LỖI khi fetch vendor: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Đã lấy {len(vendor_map)} vendor.")

    print("Đang fetch model list...")
    try:
        models = fetch_all_pages(session, "/dcl/model/models", "model", args.delay)
    except requests.RequestException as exc:
        print(f"LỖI khi fetch model: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Đã lấy {len(models)} model.")

    if args.max_records is not None:
        models = models[:args.max_records]

    unmatched_vendors = set()
    now = datetime.now(timezone.utc).isoformat()

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for m in models:
            vid = m.get("vid")
            brand = vendor_map.get(vid)
            if brand is None:
                unmatched_vendors.add(vid)
                brand = f"(unknown vendor {vid})"
            writer.writerow({
                "external_id": f"{vid}-{m.get('pid')}",
                "brand": brand,
                "model": m.get("productName") or m.get("productLabel") or "",
                "device_type_id": m.get("deviceTypeId"),
                "part_number": m.get("partNumber") or "",
                "crawled_at": now,
            })

    print(f"Xong. Tổng {len(models)} model ghi vào {args.output}")
    if unmatched_vendors:
        print(f"CẢNH BÁO: {len(unmatched_vendors)} vendorID không tìm thấy tên trong vendor list: "
              f"{sorted(unmatched_vendors)[:20]}{'...' if len(unmatched_vendors) > 20 else ''}")


if __name__ == "__main__":
    main()
