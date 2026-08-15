"""Web app thay n8n cho Track A — dashboard, trigger, settings, logs."""
from __future__ import annotations

import re
import threading
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import get_conn
from pipeline import run_full_pipeline, run_incremental_pipeline
from content_pipeline import run_content_pipeline

app = FastAPI(title="Track A — Registry Diff")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def _start_scheduler():
    import scheduler
    scheduler.start()

# Trạng thái pipeline đang chạy nền — chỉ cho 1 lần chạy tại 1 thời điểm, tránh 2 lần
# trigger đè lên nhau (crawl full mất ~15-20 phút, dễ bấm nhầm 2 lần).
_pipeline_state = {
    "running": False, "started_at": None, "result": None, "error": None, "progress": {},
}
_pipeline_lock = threading.Lock()
_stop_event = threading.Event()
_process_registry = {"proc": None}


def _run_pipeline_background(trigger_type: str):
    try:
        result = run_full_pipeline(
            trigger_type=trigger_type,
            stop_event=_stop_event,
            process_registry=_process_registry,
            progress=_pipeline_state["progress"],
        )
        _pipeline_state["result"] = result
        _pipeline_state["error"] = None
    except Exception as exc:  # noqa: BLE001 — ghi lại lỗi để dashboard hiển thị, không để mất tích âm thầm
        _pipeline_state["error"] = str(exc)
    finally:
        _pipeline_state["running"] = False
        _process_registry["proc"] = None


def _run_incremental_background(trigger_type: str):
    try:
        result = run_incremental_pipeline(
            trigger_type=trigger_type,
            process_registry=_process_registry,
            progress=_pipeline_state["progress"],
        )
        _pipeline_state["result"] = result
        _pipeline_state["error"] = None
    except Exception as exc:  # noqa: BLE001 — như _run_pipeline_background, không để mất tích âm thầm
        _pipeline_state["error"] = str(exc)
    finally:
        _pipeline_state["running"] = False
        _process_registry["proc"] = None


# State riêng cho Track B (crawl content/blog) — độc lập hoàn toàn với _pipeline_state ở
# trên (Track A, crawl sản phẩm), chạy được song song vì không đụng chung resource (khác
# site, khác bảng DB: news.* vs registry.*).
_content_state = {
    "running": False, "started_at": None, "result": None, "error": None, "progress": {},
}
_content_lock = threading.Lock()
_content_process_registry = {"proc": None}


def _run_content_background(mode: str, max_pages: int = 1, after_date: str | None = None):
    try:
        result = run_content_pipeline(
            mode=mode,
            max_pages=max_pages,
            after_date=after_date,
            process_registry=_content_process_registry,
            progress=_content_state["progress"],
        )
        _content_state["result"] = result
        _content_state["error"] = None
    except Exception as exc:  # noqa: BLE001 — không để mất tích âm thầm, giống pipeline Track A
        _content_state["error"] = str(exc)
    finally:
        _content_state["running"] = False
        _content_process_registry["proc"] = None


@app.get("/")
def dashboard(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT registry_key, run_at, item_count, new_count, removed_count, status, error, crawl_mode
            FROM registry.crawl_log
            WHERE registry_key IN ('knx', 'matter_csa')
            ORDER BY run_at DESC LIMIT 5
            """
        )
        crawl_rows = cur.fetchall()

        cur.execute(
            """
            SELECT run_at, trigger_type, device_count, send_status, error, duration_ms, message
            FROM registry.digest_log ORDER BY run_at DESC LIMIT 1
            """
        )
        last_digest = cur.fetchone()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "crawl_rows": crawl_rows,
            "last_digest": last_digest,
            "pipeline_state": _pipeline_state,
        },
    )


@app.post("/trigger")
def trigger():
    with _pipeline_lock:
        if _pipeline_state["running"]:
            return RedirectResponse("/", status_code=303)
        _pipeline_state["running"] = True
        _pipeline_state["started_at"] = datetime.now().isoformat()
        _pipeline_state["result"] = None
        _pipeline_state["error"] = None
        _pipeline_state["progress"].clear()
        _stop_event.clear()

    thread = threading.Thread(target=_run_pipeline_background, args=("manual",), daemon=True)
    thread.start()
    return RedirectResponse("/", status_code=303)


@app.post("/trigger-incremental")
def trigger_incremental():
    with _pipeline_lock:
        if _pipeline_state["running"]:
            return RedirectResponse("/", status_code=303)
        _pipeline_state["running"] = True
        _pipeline_state["started_at"] = datetime.now().isoformat()
        _pipeline_state["result"] = None
        _pipeline_state["error"] = None
        _pipeline_state["progress"].clear()
        _stop_event.clear()

    thread = threading.Thread(target=_run_incremental_background, args=("manual",), daemon=True)
    thread.start()
    return RedirectResponse("/", status_code=303)


@app.post("/stop")
def stop():
    """Ngắt pipeline đang chạy — set cờ dừng + kill process con hiện tại (nếu đang crawl)
    để không phải chờ hết bước hiện tại mới dừng."""
    _stop_event.set()
    proc = _process_registry.get("proc")
    if proc is not None and proc.poll() is None:
        proc.terminate()
    return RedirectResponse("/", status_code=303)


@app.get("/status")
def status():
    """Dashboard tự poll qua endpoint này (JS fetch) để refresh khi pipeline đang chạy."""
    return _pipeline_state


WEEKDAY_LABELS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
SOURCE_KINDS = ["manual", "html_list", "rss", "atom", "sitemap", "json_api", "search_query", "registry"]
SOURCE_CATEGORIES = ["media", "manufacturer", "distributor", "community", "standard_body", "registry", "social"]


def _slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@app.get("/settings")
def settings_page(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM registry.app_settings WHERE id = 1")
        settings = cur.fetchone()
        cur.execute("SELECT * FROM registry.brands_of_interest ORDER BY brand")
        brands = cur.fetchall()
        cur.execute("SELECT * FROM news.sources ORDER BY category, name")
        news_sources = cur.fetchall()

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "brands": brands,
            "news_sources": news_sources,
            "source_kinds": SOURCE_KINDS,
            "source_categories": SOURCE_CATEGORIES,
            "weekday_labels": WEEKDAY_LABELS,
        },
    )


@app.post("/settings/schedule")
def update_schedule(weekday: int = Form(...), hour: int = Form(...), minute: int = Form(...)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE registry.app_settings
            SET schedule_weekday = %s, schedule_hour = %s, schedule_minute = %s,
                updated_at = now()
            WHERE id = 1
            """,
            (weekday, hour, minute),
        )
        conn.commit()
    from scheduler import reschedule
    reschedule()
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/brands/add")
def add_brand(brand: str = Form(...), aliases: str = Form("")):
    alias_list = [a.strip() for a in aliases.split(",") if a.strip()]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO registry.brands_of_interest (brand, aliases) VALUES (%s, %s) "
            "ON CONFLICT (brand) DO NOTHING",
            (brand, alias_list),
        )
        conn.commit()
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/brands/{brand_id}/toggle")
def toggle_brand(brand_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE registry.brands_of_interest SET is_active = NOT is_active WHERE id = %s",
            (brand_id,),
        )
        conn.commit()
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/sources/add")
def add_source(
    name: str = Form(...),
    url: str = Form(...),
    kind: str = Form("manual"),
    category: str = Form("media"),
    lang: str = Form(""),
    region: str = Form(""),
    tier: int = Form(2),
    notes: str = Form(""),
):
    slug = _slugify(name)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO news.sources (slug, name, kind, url, lang, region, category, tier, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            """,
            (slug, name, kind, url, lang or None, region or None, category, tier, notes or None),
        )
        conn.commit()
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/sources/{source_id}/toggle")
def toggle_source(source_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE news.sources SET enabled = NOT enabled WHERE id = %s",
            (source_id,),
        )
        conn.commit()
    return RedirectResponse("/settings", status_code=303)


TEST_FETCH_USER_AGENT = "KNXStore-NewsBot/1.0 (+https://knxstore.vn; internal content pipeline tool)"


@app.post("/settings/sources/{source_id}/test")
def test_source(source_id: int):
    """Test nhanh 1 nguồn — chỉ fetch + kiểm tra selector, KHÔNG lưu gì vào news.articles.
    Dùng để xác nhận nguồn còn sống + extract_rule còn khớp mà không cần chạy full fetch."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM news.sources WHERE id = %s", (source_id,))
        source = cur.fetchone()

    if source is None:
        return {"ok": False, "error": "Không tìm thấy nguồn"}

    if source["requires_js"]:
        return {"ok": False, "error": "requires_js=true — cần Playwright (B6, chưa build), không test được kiểu này"}

    try:
        resp = requests.get(source["url"], headers={"User-Agent": TEST_FETCH_USER_AGENT}, timeout=15)
    except requests.RequestException as exc:
        return {"ok": False, "error": f"Fetch lỗi: {exc}"}

    result = {"ok": resp.status_code == 200, "http_status": resp.status_code, "size_bytes": len(resp.content)}
    if not result["ok"]:
        return result

    if source["kind"] == "manual":
        result["detail"] = "manual (1 URL = 1 bài) — status OK là đủ, không cần selector"
        return result

    if source["kind"] == "html_list":
        rule = source["extract_rule"] or {}
        card_selector, link_selector = rule.get("card_selector"), rule.get("link_selector")
        if not card_selector or not link_selector:
            result["error"] = "extract_rule thiếu card_selector/link_selector"
            return result
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(card_selector)
        sample_titles = []
        for card in cards[:5]:
            link = card.select_one(link_selector)
            if link:
                sample_titles.append(link.get_text(strip=True)[:60])
        result["candidate_count"] = len(cards)
        result["sample_titles"] = sample_titles
        if len(cards) == 0:
            result["ok"] = False
            result["error"] = "0 card khớp card_selector — site đổi giao diện hoặc selector sai"
        return result

    return {"ok": False, "error": f"kind '{source['kind']}' chưa hỗ trợ test"}


@app.get("/content")
def content_page(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) AS total FROM news.articles")
        total_articles = cur.fetchone()["total"]

        cur.execute("SELECT full_fetch_max_pages, full_fetch_after_date FROM news.content_settings WHERE id = 1")
        content_settings = cur.fetchone()

        cur.execute(
            """
            SELECT s.slug, s.kind, s.tier, s.enabled, s.requires_js,
                   h.last_attempt_at, h.last_success_at, h.consecutive_failures, h.last_error,
                   (SELECT count(*) FROM news.articles a WHERE a.source_id = s.id) AS article_count
            FROM news.sources s
            LEFT JOIN news.source_health h ON h.source_id = s.id
            ORDER BY s.tier, s.slug
            """
        )
        source_rows = cur.fetchall()

        cur.execute(
            """
            SELECT s.slug, f.fetched_at, f.http_status, f.item_count, f.new_count, f.duration_ms, f.error
            FROM news.fetch_log f JOIN news.sources s ON s.id = f.source_id
            ORDER BY f.fetched_at DESC LIMIT 15
            """
        )
        fetch_rows = cur.fetchall()

    return templates.TemplateResponse(
        "content.html",
        {
            "request": request,
            "total_articles": total_articles,
            "source_rows": source_rows,
            "fetch_rows": fetch_rows,
            "content_state": _content_state,
            "content_settings": content_settings,
        },
    )


@app.post("/content/settings/max-pages")
def content_update_max_pages(full_fetch_max_pages: int = Form(...), full_fetch_after_date: str = Form("")):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE news.content_settings
            SET full_fetch_max_pages = %s, full_fetch_after_date = %s, updated_at = now()
            WHERE id = 1
            """,
            (full_fetch_max_pages, full_fetch_after_date or None),
        )
        conn.commit()
    return RedirectResponse("/content", status_code=303)


@app.post("/content/trigger-full")
def content_trigger_full():
    with _content_lock:
        if _content_state["running"]:
            return RedirectResponse("/content", status_code=303)
        _content_state["running"] = True
        _content_state["started_at"] = datetime.now().isoformat()
        _content_state["result"] = None
        _content_state["error"] = None
        _content_state["progress"].clear()

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT full_fetch_max_pages, full_fetch_after_date FROM news.content_settings WHERE id = 1")
        settings_row = cur.fetchone()
        max_pages = settings_row["full_fetch_max_pages"]
        after_date = settings_row["full_fetch_after_date"]

    thread = threading.Thread(
        target=_run_content_background, args=("full", max_pages, str(after_date) if after_date else None),
        daemon=True,
    )
    thread.start()
    return RedirectResponse("/content", status_code=303)


@app.post("/content/trigger-latest")
def content_trigger_latest():
    with _content_lock:
        if _content_state["running"]:
            return RedirectResponse("/content", status_code=303)
        _content_state["running"] = True
        _content_state["started_at"] = datetime.now().isoformat()
        _content_state["result"] = None
        _content_state["error"] = None
        _content_state["progress"].clear()

    thread = threading.Thread(target=_run_content_background, args=("latest",), daemon=True)
    thread.start()
    return RedirectResponse("/content", status_code=303)


@app.post("/content/stop")
def content_stop():
    proc = _content_process_registry.get("proc")
    if proc is not None and proc.poll() is None:
        proc.terminate()
    return RedirectResponse("/content", status_code=303)


@app.get("/content/status")
def content_status():
    return _content_state


ARTICLES_PAGE_SIZE = 30


@app.get("/content/articles")
def content_articles_page(request: Request, page: int = 1, source_slug: str = "", q: str = ""):
    page = max(page, 1)
    offset = (page - 1) * ARTICLES_PAGE_SIZE

    where_clauses = []
    params: list = []
    if source_slug:
        where_clauses.append("s.slug = %s")
        params.append(source_slug)
    if q:
        where_clauses.append("a.title ILIKE %s")
        params.append(f"%{q}%")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT count(*) AS total FROM news.articles a JOIN news.sources s ON s.id = a.source_id {where_sql}",
            params,
        )
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            SELECT a.id, a.title, a.author, a.published_at, a.first_seen_at, a.word_count,
                   a.extract_status, a.original_url, s.slug AS source_slug, s.tier
            FROM news.articles a JOIN news.sources s ON s.id = a.source_id
            {where_sql}
            ORDER BY a.first_seen_at DESC
            LIMIT %s OFFSET %s
            """,
            (*params, ARTICLES_PAGE_SIZE, offset),
        )
        articles = cur.fetchall()

        cur.execute("SELECT slug FROM news.sources ORDER BY slug")
        all_source_slugs = [r["slug"] for r in cur.fetchall()]

    total_pages = max((total + ARTICLES_PAGE_SIZE - 1) // ARTICLES_PAGE_SIZE, 1)

    return templates.TemplateResponse(
        "content_articles.html",
        {
            "request": request,
            "articles": articles,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "all_source_slugs": all_source_slugs,
            "selected_source_slug": source_slug,
            "selected_q": q,
        },
    )


@app.get("/content/articles/{article_id}")
def content_article_detail(request: Request, article_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.*, s.slug AS source_slug, s.name AS source_name, s.url AS source_url, s.tier
            FROM news.articles a JOIN news.sources s ON s.id = a.source_id
            WHERE a.id = %s
            """,
            (article_id,),
        )
        article = cur.fetchone()

    if article is None:
        return RedirectResponse("/content/articles", status_code=303)

    return templates.TemplateResponse(
        "content_article_detail.html",
        {"request": request, "article": article},
    )


PRODUCTS_PAGE_SIZE = 50
REGISTRY_KEYS = ["knx", "matter_csa", "dali"]


@app.get("/products")
def products_page(request: Request, page: int = 1, registry: str = "", brand: str = "", model: str = ""):
    page = max(page, 1)
    offset = (page - 1) * PRODUCTS_PAGE_SIZE

    where_clauses = []
    params: list = []
    if registry:
        where_clauses.append("registry_key = %s")
        params.append(registry)
    if brand:
        where_clauses.append("brand ILIKE %s")
        params.append(f"%{brand}%")
    if model:
        where_clauses.append("model ILIKE %s")
        params.append(f"%{model}%")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT count(*) AS total FROM registry.devices {where_sql}", params)
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            SELECT registry_key, external_id, brand, model, category, first_seen_at, status, attributes
            FROM registry.devices
            {where_sql}
            ORDER BY first_seen_at DESC, brand
            LIMIT %s OFFSET %s
            """,
            (*params, PRODUCTS_PAGE_SIZE, offset),
        )
        devices = cur.fetchall()

        cur.execute("SELECT DISTINCT brand FROM registry.devices ORDER BY brand")
        all_brands = [r["brand"] for r in cur.fetchall()]

    total_pages = max((total + PRODUCTS_PAGE_SIZE - 1) // PRODUCTS_PAGE_SIZE, 1)

    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "devices": devices,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "registry_keys": REGISTRY_KEYS,
            "all_brands": all_brands,
            "selected_registry": registry,
            "selected_brand": brand,
            "selected_model": model,
        },
    )


@app.get("/products/{registry_key}/{external_id}")
def product_detail(request: Request, registry_key: str, external_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM registry.devices WHERE registry_key = %s AND external_id = %s",
            (registry_key, external_id),
        )
        device = cur.fetchone()

        crawl_rows = []
        if device is not None:
            cur.execute(
                """
                SELECT run_at, item_count, new_count, removed_count, status, crawl_mode
                FROM registry.crawl_log WHERE registry_key = %s
                ORDER BY run_at DESC LIMIT 5
                """,
                (registry_key,),
            )
            crawl_rows = cur.fetchall()

    if device is None:
        return RedirectResponse("/products", status_code=303)

    return templates.TemplateResponse(
        "product_detail.html",
        {"request": request, "device": device, "crawl_rows": crawl_rows},
    )


@app.get("/logs")
def logs_page(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM registry.crawl_log ORDER BY run_at DESC LIMIT 20"
        )
        crawl_logs = cur.fetchall()
        cur.execute(
            "SELECT * FROM registry.digest_log ORDER BY run_at DESC LIMIT 20"
        )
        digest_logs = cur.fetchall()

    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "crawl_logs": crawl_logs, "digest_logs": digest_logs},
    )
