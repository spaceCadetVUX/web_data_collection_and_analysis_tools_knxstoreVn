#!/usr/bin/env python3
"""
Crawl KNX certified devices listing (knx.org/devices) -> CSV.

Chỉ crawl trang danh sách (không vào trang chi tiết) — đủ cho brand + model + link,
đúng nhu cầu Track A (registry diff). Xem track-a/A2-knx-crawler.md để biết lý do
category/device_type bị bỏ ở v1.

Cách chạy (test trên 3 trang ~36 thiết bị trước khi chạy full):
    python3 crawl_knx_devices.py --max-pages 3 --output test_run.csv

Chạy full (848 trang, ~10.167 thiết bị):
    python3 crawl_knx_devices.py --output knx_devices.csv

Resume sau khi bị đứt giữa chừng (ví dụ dừng ở trang 400):
    python3 crawl_knx_devices.py --start-page 400 --output knx_devices.csv --append
"""

import argparse
import csv
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.knx.org/devices"
USER_AGENT = "KNXStore-RegistryBot/1.0 (+https://knxstore.vn; internal registry diff tool)"
CSV_FIELDS = ["external_id", "brand", "model", "source_url", "crawled_at"]


def fetch_page(session, page_number):
    resp = session.get(BASE_URL, params={"page": page_number}, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_result_count(html):
    match = re.search(r'([\d,]+)\s*Results', html)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_cards(html):
    """Trả về list dict {external_id, brand, model, source_url} từ 1 trang danh sách."""
    soup = BeautifulSoup(html, "html.parser")
    devices = []
    for card in soup.select("article.node-device-card"):
        link = card.select_one("a.node-device-card__wrapper")
        if not link or not link.get("href"):
            continue
        href = link["href"]
        slug = href.rstrip("/").split("/")[-1]

        title_el = card.select_one(".node-device-card__content h4")
        brand_el = card.select_one(".node-device-card__content span")

        model = title_el.get_text(strip=True) if title_el else ""
        brand = brand_el.get_text(strip=True) if brand_el else ""

        devices.append({
            "external_id": slug,
            "brand": brand,
            "model": model,
            "source_url": f"https://www.knx.org{href}",
        })
    return devices


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="knx_devices.csv", help="File CSV output")
    parser.add_argument("--max-pages", type=int, default=None,
                         help="Giới hạn số trang crawl (dùng khi test). Bỏ trống = crawl hết.")
    parser.add_argument("--start-page", type=int, default=0, help="Trang bắt đầu (0-indexed, để resume)")
    parser.add_argument("--delay", type=float, default=1.0, help="Giây nghỉ giữa mỗi request")
    parser.add_argument("--append", action="store_true", help="Ghi nối vào CSV có sẵn thay vì ghi đè")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    mode = "a" if args.append else "w"
    write_header = not (args.append)

    with open(args.output, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()

        page = args.start_page
        total_results = None
        total_pages = None
        collected = 0

        while True:
            if args.max_pages is not None and (page - args.start_page) >= args.max_pages:
                print(f"Đạt giới hạn --max-pages={args.max_pages}, dừng ở trang {page}.")
                break

            try:
                html = fetch_page(session, page)
            except requests.RequestException as exc:
                print(f"LỖI ở trang {page}: {exc}. Dừng lại — chạy lại với --start-page {page} để tiếp tục.",
                      file=sys.stderr)
                sys.exit(1)

            if total_results is None:
                total_results = parse_result_count(html)
                if total_results:
                    total_pages = -(-total_results // 12)  # ceil division, 12 device/trang
                    print(f"Tổng {total_results} thiết bị, ước tính {total_pages} trang.")

            devices = parse_cards(html)
            if not devices:
                print(f"Trang {page} không có thiết bị nào — có thể đã hết trang, dừng lại.")
                break

            now = datetime.now(timezone.utc).isoformat()
            for d in devices:
                d["crawled_at"] = now
                writer.writerow(d)
            f.flush()  # ghi ngay xuống đĩa, không mất dữ liệu nếu crash giữa chừng

            collected += len(devices)
            if page % 20 == 0:
                print(f"Trang {page}: +{len(devices)} thiết bị (tổng đã crawl: {collected})")

            if total_pages is not None and page >= total_pages - 1:
                print(f"Đã crawl hết {total_pages} trang.")
                break

            page += 1
            time.sleep(args.delay)

    print(f"Xong. Tổng {collected} thiết bị ghi vào {args.output}")


if __name__ == "__main__":
    main()
