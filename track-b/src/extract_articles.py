#!/usr/bin/env python3
"""
Crawl + extract nội dung bài viết cho Track B (news pipeline) — đọc danh sách nguồn từ
news.sources, ghi bài viết đã bóc tách vào news.articles, log vào news.fetch_log +
news.source_health. Tách biệt hoàn toàn với track-a/src/ (crawl sản phẩm KNX/Matter).

2 kind nguồn được hỗ trợ (xem CHECK constraint news.sources.kind):
  - manual: 1 URL = 1 bài viết cụ thể, fetch + extract thẳng.
  - html_list: URL là trang chuyên mục/listing — bóc tách link bài con qua
    extract_rule.list_selector (CSS selector, xem migration 0008), rồi fetch + extract
    từng bài con như "manual".

Dedupe 2 tầng (docs/plan.md §5.1, §5.2), cả 2 làm ngay trong script này:
  - Tầng 1: canonical URL (bỏ tracking param) — UNIQUE constraint trên
    news.articles.canonical_url là chốt chặn cuối.
  - Tầng 2: SimHash 64-bit trên body_text, Hamming distance <= 3 coi là trùng — query qua
    4 band index (simhash_b0..b3, pigeonhole principle) rồi tính Hamming chính xác trên tập
    candidate, xem find_near_duplicate(). Bài trùng bị bỏ qua (không insert), không phải lỗi.

Nguồn requires_js=true (hiện chỉ có androidcentral-smart-home) bị BỎ QUA hoàn toàn — set này
cần Playwright (B6, chưa build) để lấy được link/nội dung thật, fetch bằng requests thường
chỉ ra rỗng hoặc sai.

Cách chạy:
    python3 extract_articles.py --db-url postgresql://user:pass@host:port/db
    python3 extract_articles.py --db-url ... --source-slug the-ambient-news-matter  # test 1 nguồn
    python3 extract_articles.py --db-url ... --max-new-per-source 5                 # giới hạn khi test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import psycopg2
import psycopg2.extras
import requests
import trafilatura
from bs4 import BeautifulSoup

USER_AGENT = "KNXStore-NewsBot/1.0 (+https://knxstore.vn; internal content pipeline tool)"

# Query param nào bắt đầu bằng các prefix này bị strip khi tính canonical_url — dựa theo
# yêu cầu dedupe tầng 1 ở docs/plan.md §5.1 ("20 URL có tracking param, gồm cả spm và
# WeChat param").
TRACKING_PARAM_PREFIXES = ("utm_", "fbclid", "gclid", "yclid", "mc_cid", "mc_eid", "spm",
                           "igshid", "ref_src", "_ga", "from")


def canonicalize_url(url: str) -> str:
    """Bỏ tracking param + chuẩn hoá scheme/host/path để 2 URL cùng trỏ 1 bài (chỉ khác
    tracking param) ra cùng 1 canonical_url — dedupe tầng 1."""
    parsed = urlsplit(url)
    kept_params = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not any(k.lower() == p or k.lower().startswith(p) for p in TRACKING_PARAM_PREFIXES)
    ]
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(kept_params)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))


def _simhash(text: str, bits: int = 64) -> int:
    """SimHash 64-bit chuẩn (word-level, không phải shingle) — đủ cho near-dup detection
    ở B2 sau này. Không cần thư viện ngoài, tự cài bằng hashlib cho gọn."""
    if not text:
        return 0
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return 0
    v = [0] * bits
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        for i in range(bits):
            v[i] += 1 if (h >> i) & 1 else -1
    fingerprint = 0
    for i in range(bits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint  # unsigned 0..2^64-1 — dùng nguyên dạng này cho _simhash_bands


def _to_signed_bigint(unsigned_64: int) -> int:
    """Postgres bigint là signed 64-bit (-2^63..2^63-1); _simhash trả unsigned 64-bit —
    không convert sẽ lỗi 'NumericValueOutOfRange' khi bit 63 bật. Chỉ áp dụng lúc lưu cột
    simhash, KHÔNG áp dụng trước khi tách band (xem _simhash_bands, cần giá trị unsigned)."""
    return unsigned_64 - (1 << 64) if unsigned_64 >= (1 << 63) else unsigned_64


def _simhash_bands(fingerprint: int) -> tuple[int, int, int, int]:
    """Tách fingerprint 64-bit thành 4 band 16-bit — dùng để index (simhash_b0..b3), so
    khớp gần đúng (Hamming distance nhỏ) nhanh hơn quét toàn bộ bảng ở B2."""
    mask16 = (1 << 16) - 1
    return tuple((fingerprint >> (i * 16)) & mask16 for i in range(4))


_MASK64 = (1 << 64) - 1
HAMMING_THRESHOLD = 3  # xem docs/plan.md §5.2 — 2 bài coi là trùng nếu Hamming distance <= 3


def _hamming_distance(a_signed: int, b_signed: int) -> int:
    """XOR trên biểu diễn unsigned 64-bit (mask lại vì Python int âm bị sign-extend vô hạn),
    rồi đếm bit khác nhau."""
    return bin((a_signed & _MASK64) ^ (b_signed & _MASK64)).count("1")


def find_near_duplicate(cur, fingerprint_signed: int, b0: int, b1: int, b2: int, b3: int):
    """Dedupe tầng 2 (docs/plan.md §5.2): pigeonhole — nếu Hamming distance <= 3 trên 64 bit
    chia 4 band 16-bit, ít nhất 1 band phải trùng hệt. Query theo band index (không quét toàn
    bảng), rồi tính Hamming chính xác trên tập candidate. Trả (article_id, distance) của bài
    trùng gần nhất nếu có, ngược lại (None, None)."""
    cur.execute(
        """
        SELECT id, title, simhash FROM news.articles
        WHERE simhash_b0 = %s OR simhash_b1 = %s OR simhash_b2 = %s OR simhash_b3 = %s
        """,
        (b0, b1, b2, b3),
    )
    best_id, best_title, best_distance = None, None, None
    for row in cur.fetchall():
        if row["simhash"] is None:
            continue
        distance = _hamming_distance(fingerprint_signed, row["simhash"])
        if distance <= HAMMING_THRESHOLD and (best_distance is None or distance < best_distance):
            best_id, best_title, best_distance = row["id"], row["title"], distance
    return best_id, best_title, best_distance


def _extract_links(html: str, selector: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select(selector):
        href = a.get("href")
        if href:
            urls.append(urljoin(base_url, href))
    return urls


def discover_article_urls(session: requests.Session, source: dict, max_pages: int = 1) -> list[str]:
    """Trả list URL bài viết cần fetch cho 1 nguồn. kind=manual -> chính URL đó. kind=html_list
    -> bóc tách link con qua extract_rule.list_selector, giữ nguyên thứ tự xuất hiện, loại
    trùng lặp trong cùng 1 lần bóc tách.

    max_pages > 1 + có extract_rule.page_url_template -> lật thêm trang 2..max_pages (dùng
    "Fetch toàn bộ") — xem migration 0010 để biết pattern đã verify thật cho từng site (không
    phải site nào cũng dùng /page/N/, và không phải site nào cũng CÓ nhiều hơn 1 trang — thiếu
    page_url_template nghĩa là chỉ có đúng 1 trang, verify thật, không phải thiếu sót)."""
    if source["kind"] == "manual":
        return [source["url"]]

    if source["kind"] == "html_list":
        rule = source["extract_rule"] or {}
        selector = rule.get("list_selector")
        if not selector:
            raise ValueError(
                f"Nguồn '{source['slug']}' kind=html_list nhưng extract_rule.list_selector "
                f"rỗng — không biết bóc tách link bài con thế nào."
            )
        resp = session.get(source["url"], timeout=20)
        resp.raise_for_status()

        seen, urls = set(), []
        for u in _extract_links(resp.text, selector, source["url"]):
            if u not in seen:
                seen.add(u)
                urls.append(u)

        template = rule.get("page_url_template")
        if max_pages > 1 and template:
            for n in range(2, max_pages + 1):
                page_url = template.format(n=n)
                resp = session.get(page_url, timeout=20)
                if resp.status_code == 404:
                    print(f"  (trang {n}: 404 — đã hết trang thật, dừng lật trang)")
                    break
                resp.raise_for_status()
                page_urls = _extract_links(resp.text, selector, page_url)
                new_on_page = [u for u in page_urls if u not in seen]
                if not new_on_page:
                    print(f"  (trang {n}: không có link mới nào — dừng lật trang, có thể "
                          f"site redirect ngược về trang trước)")
                    break
                for u in new_on_page:
                    seen.add(u)
                    urls.append(u)
        return urls

    raise ValueError(f"kind '{source['kind']}' chưa hỗ trợ — script này chỉ xử lý manual/html_list")


def extract_article(session: requests.Session, url: str) -> dict | None:
    """Fetch 1 URL bài viết + bóc tách bằng trafilatura. Trả None nếu fetch lỗi hoặc
    trafilatura không bóc được nội dung (trang rỗng/chặn bot/không phải bài viết thật)."""
    resp = session.get(url, timeout=20)
    resp.raise_for_status()

    extracted_json = trafilatura.extract(
        resp.text, url=url, output_format="json", with_metadata=True,
        favor_precision=True,
    )
    if not extracted_json:
        return None

    data = json.loads(extracted_json)
    body_text = (data.get("text") or "").strip()
    if not body_text:
        return None

    return {
        "title": data.get("title"),
        "author": data.get("author"),
        "published_at": data.get("date"),  # ISO string hoặc None — cột published_at "KHÔNG tin cậy" (xem schema)
        "body_text": body_text,
    }


def process_source(conn, session: requests.Session, source: dict,
                    max_new: int, delay: float, max_pages: int = 1) -> None:
    cur = conn.cursor()
    label = source["slug"]
    started = time.monotonic()
    item_count, new_count, dup_count = 0, 0, 0
    fetch_error = None
    http_status = None

    try:
        if source["requires_js"]:
            # Không thử fetch — biết trước sẽ ra rỗng/sai (xem migration 0008, ghi chú
            # androidcentral-smart-home). Cần Playwright (B6, chưa build).
            fetch_error = "requires_js=true, chưa có renderer (B6) — bỏ qua"
            print(f"[{label}] SKIP: {fetch_error}")
            return

        try:
            candidate_urls = discover_article_urls(session, source, max_pages=max_pages)
            http_status = 200
        except requests.RequestException as exc:
            http_status = getattr(exc.response, "status_code", None)
            fetch_error = f"Lỗi fetch trang listing: {exc}"
            print(f"[{label}] LỖI: {fetch_error}", file=sys.stderr)
            return

        item_count = len(candidate_urls)
        print(f"[{label}] Tìm thấy {item_count} URL ứng viên.")

        for url in candidate_urls:
            if new_count >= max_new:
                print(f"[{label}] Đạt --max-new-per-source={max_new}, dừng nguồn này "
                      f"(còn {item_count - new_count} URL chưa xét, sẽ xét ở lần chạy sau).")
                break

            canonical = canonicalize_url(url)
            cur.execute("SELECT 1 FROM news.articles WHERE canonical_url = %s", (canonical,))
            if cur.fetchone():
                continue  # đã có, bỏ qua — không tính vào new_count

            try:
                article = extract_article(session, url)
            except requests.RequestException as exc:
                print(f"[{label}] LỖI fetch bài {url}: {exc}", file=sys.stderr)
                continue

            if article is None:
                print(f"[{label}] Không bóc tách được nội dung: {url}")
                continue

            try:
                fingerprint = _simhash(article["body_text"])
                b0, b1, b2, b3 = _simhash_bands(fingerprint)
                fingerprint_signed = _to_signed_bigint(fingerprint)
                word_count = len(article["body_text"].split())

                dup_id, dup_title, dup_distance = find_near_duplicate(cur, fingerprint_signed, b0, b1, b2, b3)
                if dup_id is not None:
                    dup_count += 1
                    print(f"[{label}] ~ Trùng nội dung (Hamming={dup_distance}) với bài đã có "
                          f"{dup_title!r}, bỏ qua: {article['title']!r}")
                    conn.commit()  # commit để giữ nguyên state sạch, không có gì để rollback
                    time.sleep(delay)
                    continue

                cur.execute(
                    """
                    INSERT INTO news.articles
                        (source_id, canonical_url, original_url, title, author, published_at,
                         lang, body_text, word_count, simhash, simhash_b0, simhash_b1,
                         simhash_b2, simhash_b3, extract_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ok')
                    ON CONFLICT (canonical_url) DO NOTHING
                    """,
                    (source["id"], canonical, url, article["title"], article["author"],
                     article["published_at"], source["lang"], article["body_text"], word_count,
                     fingerprint_signed, b0, b1, b2, b3),
                )
                if cur.rowcount:
                    new_count += 1
                    print(f"[{label}] + Bài mới: {article['title']!r} ({word_count} từ)")
                conn.commit()
            except Exception as exc:  # noqa: BLE001 — 1 bài lỗi không được kéo sập cả nguồn
                conn.rollback()
                print(f"[{label}] LỖI lưu bài {url}: {exc}", file=sys.stderr)
                continue

            time.sleep(delay)

        if dup_count:
            print(f"[{label}] Bỏ qua {dup_count} bài trùng nội dung (SimHash, dedupe tầng 2).")

    finally:
        conn.rollback()  # đảm bảo transaction sạch nếu có exception chưa được bắt ở trên
        duration_ms = int((time.monotonic() - started) * 1000)
        cur.execute(
            """
            INSERT INTO news.fetch_log (source_id, http_status, item_count, new_count, duration_ms, error)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (source["id"], http_status, item_count, new_count, duration_ms, fetch_error),
        )
        cur.execute(
            """
            INSERT INTO news.source_health (source_id, last_attempt_at, last_success_at, consecutive_failures, last_error)
            VALUES (%s, now(), CASE WHEN %s IS NULL THEN now() ELSE NULL END, CASE WHEN %s IS NULL THEN 0 ELSE 1 END, %s)
            ON CONFLICT (source_id) DO UPDATE SET
                last_attempt_at = now(),
                last_success_at = CASE WHEN %s IS NULL THEN now() ELSE news.source_health.last_success_at END,
                consecutive_failures = CASE WHEN %s IS NULL THEN 0 ELSE news.source_health.consecutive_failures + 1 END,
                last_error = COALESCE(%s, news.source_health.last_error)
            """,
            (source["id"], fetch_error, fetch_error, fetch_error,
             fetch_error, fetch_error, fetch_error),
        )
        conn.commit()
        cur.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-url", required=True, help="postgresql://user:pass@host:port/db")
    parser.add_argument("--source-slug", default=None, help="Chỉ chạy 1 nguồn (test) thay vì toàn bộ")
    parser.add_argument("--max-new-per-source", type=int, default=10,
                         help="Giới hạn số bài MỚI lấy mỗi nguồn/lần chạy (mặc định 10 — "
                              "tránh lần đầu chạy 1 nguồn có hàng trăm bài lịch sử kéo hết về)")
    parser.add_argument("--delay", type=float, default=1.0, help="Giây nghỉ giữa mỗi request fetch bài")
    parser.add_argument("--max-pages", type=int, default=1,
                         help="Số trang listing lật qua mỗi nguồn html_list, tính từ trang mới "
                              "nhất (trang 1 = news.sources.url). Mặc định 1 (không lật trang) — "
                              "'Fetch toàn bộ' nên truyền số lớn hơn. Nguồn không có "
                              "extract_rule.page_url_template chỉ có đúng 1 trang thật, tham số "
                              "này không có tác dụng với nguồn đó (xem migration 0010).")
    args = parser.parse_args()

    conn = psycopg2.connect(args.db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False

    with conn.cursor() as cur:
        if args.source_slug:
            cur.execute("SELECT * FROM news.sources WHERE slug = %s AND enabled", (args.source_slug,))
        else:
            cur.execute("SELECT * FROM news.sources WHERE enabled ORDER BY tier, slug")
        sources = cur.fetchall()

    if not sources:
        print("Không có nguồn nào (kiểm tra --source-slug hoặc enabled=true).", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print(f"Chạy {len(sources)} nguồn, tối đa {args.max_new_per_source} bài mới/nguồn.")
    failed_sources = []
    for source in sources:
        try:
            process_source(conn, session, source, args.max_new_per_source, args.delay, args.max_pages)
        except Exception as exc:  # noqa: BLE001 — 1 nguồn lỗi không được giết cả batch 35 nguồn
            conn.rollback()
            failed_sources.append(source["slug"])
            print(f"[{source['slug']}] LỖI KHÔNG XỬ LÝ ĐƯỢC, bỏ qua nguồn này: {exc}", file=sys.stderr)

    conn.close()
    if failed_sources:
        print(f"Xong, nhưng {len(failed_sources)} nguồn lỗi không xử lý được: {failed_sources}")
    else:
        print("Xong.")


if __name__ == "__main__":
    main()
