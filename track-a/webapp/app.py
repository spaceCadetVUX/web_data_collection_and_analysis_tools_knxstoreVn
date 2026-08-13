"""Web app thay n8n cho Track A — dashboard, trigger, settings, logs."""
from __future__ import annotations

import threading
from datetime import datetime

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import get_conn
from pipeline import run_full_pipeline

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


@app.get("/")
def dashboard(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT registry_key, run_at, item_count, new_count, removed_count, status, error
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


@app.get("/settings")
def settings_page(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM registry.app_settings WHERE id = 1")
        settings = cur.fetchone()
        cur.execute("SELECT * FROM registry.brands_of_interest ORDER BY brand")
        brands = cur.fetchall()

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "brands": brands,
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
            SELECT registry_key, brand, model, category, first_seen_at, status, attributes
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
