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
    parser.add_argument("--known-ids-file", default=None,
                         help="File text, mỗi dòng 1 external_id đã có trong DB. Bật chế độ "
                              "incremental: trang danh sách sắp xếp mới nhất trước, nên dừng "
                              "sớm khi gặp đủ --stable-pages-to-stop trang liên tiếp không có "
                              "thiết bị nào ngoài known-ids — không cần crawl hết 848 trang chỉ "
                              "để tìm thiết bị mới.")
    parser.add_argument("--stable-pages-to-stop", type=int, default=2,
                         help="Số trang liên tiếp toàn thiết bị đã biết trước khi dừng (chỉ dùng "
                              "cùng --known-ids-file). Mặc định 2 để có biên an toàn.")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    known_ids = None
    if args.known_ids_file:
        with open(args.known_ids_file, encoding="utf-8") as f:
            known_ids = {line.strip() for line in f if line.strip()}
        print(f"Chế độ incremental: {len(known_ids)} external_id đã biết, dừng sau "
              f"{args.stable_pages_to_stop} trang liên tiếp không có thiết bị mới.")

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
        stable_streak = 0

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
                if total_pages is not None and page < total_pages - 1:
                    # Trang rỗng NHƯNG chưa đạt số trang ước tính — khả năng cao là lỗi tạm
                    # thời (site trả HTML lỗi/rỗng 1 nhịp) chứ không phải hết trang thật. Nếu
                    # coi đây là "xong" và trả về returncode=0, import_and_diff.py sẽ đánh dấu
                    # TOÀN BỘ thiết bị chưa crawl tới (có thể hàng nghìn) là 'removed' — sự cố
                    # thật đã xảy ra 2026-08-14: 186 thiết bị GIRA/MDT/ABB/Schneider/Siemens bị
                    # đánh dấu removed sai chỉ vì 1 trang giữa chừng rỗng bất thường. Thoát với
                    # exit code khác 0 để _run_tracked coi là fail, KHÔNG chạy import.
                    print(f"LỖI ở trang {page}: trang rỗng nhưng mới đạt {page}/{total_pages} "
                          f"trang ước tính — nghi site trả lỗi tạm thời, KHÔNG phải hết trang "
                          f"thật. Dừng lại, không ghi 'đã xong' để tránh import đánh dấu nhầm "
                          f"phần chưa crawl là removed. Chạy lại với --start-page {page} để tiếp tục.",
                          file=sys.stderr)
                    sys.exit(1)
                print(f"Trang {page} không có thiết bị nào — đã đạt/vượt {total_pages or '?'} "
                      f"trang ước tính, đúng là hết trang thật, dừng lại.")
                break

            now = datetime.now(timezone.utc).isoformat()
            for d in devices:
                d["crawled_at"] = now
                writer.writerow(d)
            f.flush()  # ghi ngay xuống đĩa, không mất dữ liệu nếu crash giữa chừng

            collected += len(devices)
            if page % 20 == 0:
                print(f"Trang {page}: +{len(devices)} thiết bị (tổng đã crawl: {collected})")

            if known_ids is not None:
                new_on_page = [d for d in devices if d["external_id"] not in known_ids]
                if new_on_page:
                    stable_streak = 0
                    print(f"Trang {page}: {len(new_on_page)} thiết bị MỚI "
                          f"({', '.join(d['external_id'] for d in new_on_page[:5])}"
                          f"{'...' if len(new_on_page) > 5 else ''})")
                else:
                    stable_streak += 1
                    if stable_streak >= args.stable_pages_to_stop:
                        print(f"Đủ {stable_streak} trang liên tiếp không có thiết bị mới — "
                              f"dừng ở trang {page} (incremental).")
                        break

            if total_pages is not None and page >= total_pages - 1:
                print(f"Đã crawl hết {total_pages} trang.")
                break

            page += 1
            time.sleep(args.delay)

    print(f"Xong. Tổng {collected} thiết bị ghi vào {args.output}")


if __name__ == "__main__":
    main()
