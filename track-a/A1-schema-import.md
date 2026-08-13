# A1 — Schema `registry` + import CSV KNX

Ước tính: 3-4h · Phụ thuộc: không · Xem [00-overview.md](00-overview.md) cho bối cảnh.

## Mục tiêu

Tạo schema `registry` trên Postgres 5433 (pgvector:pg17, cùng instance đang chạy cho n8n),
import 10.195 device KNX từ CSV có sẵn thành baseline snapshot đầu tiên.

## Schema (theo `knx-news-agent-plan.md` §4.3, giữ nguyên)

```sql
CREATE SCHEMA IF NOT EXISTS registry;

CREATE TABLE registry.snapshots (
  id           bigserial PRIMARY KEY,
  registry_key text,        -- knx | matter_csa | dali
  taken_at     timestamptz DEFAULT now(),
  item_count   int,
  raw          jsonb
);

CREATE TABLE registry.devices (
  id            bigserial PRIMARY KEY,
  registry_key  text,
  external_id   text,
  brand         text,
  model         text,
  category      text,
  device_type   text,
  cert_date     date,
  attributes    jsonb,
  first_seen_at timestamptz DEFAULT now(),
  last_seen_at  timestamptz DEFAULT now(),
  status        text DEFAULT 'active',   -- active | removed
  UNIQUE (registry_key, external_id)
);
CREATE INDEX ON registry.devices (brand);
CREATE INDEX ON registry.devices (first_seen_at DESC);
```

**Thêm mới so với §4.3** (lý do ở [00-overview.md](00-overview.md) mục 2):

```sql
CREATE TABLE registry.brands_of_interest (
  id         serial PRIMARY KEY,
  brand      text UNIQUE NOT NULL,
  aliases    text[],        -- ['ABB','ABB i-bus','Busch-Jaeger']
  aliases_zh text[],        -- tên tiếng Trung
  priority   smallint DEFAULT 2,
  is_active  boolean DEFAULT true
);

CREATE TABLE registry.crawl_log (
  id           bigserial PRIMARY KEY,
  registry_key text NOT NULL,
  run_at       timestamptz DEFAULT now(),
  item_count   int,
  new_count    int,
  removed_count int,
  status       text,        -- ok | failed | aborted_anomaly
  error        text,
  duration_ms  int
);
CREATE INDEX ON registry.crawl_log (registry_key, run_at DESC);
```

## Migration script

Dùng convention file đánh số, chạy bằng `psql -f` hoặc tool migration đang có sẵn trong n8n
stack (xác nhận với dev nếu team đã dùng Flyway/Sqitch/tự viết):

```
migrations/
  0001_create_registry_schema.sql   -- toàn bộ DDL ở trên
  0001_create_registry_schema.down.sql  -- DROP SCHEMA registry CASCADE
```

**Rollback bắt buộc có** — theo đúng tiêu chuẩn DoD của B0 bên Track B (§10), áp dụng nhất
quán cho Track A.

## Import CSV — CSV cũ không còn cần thiết, dùng output của crawler A2 thay thế

Không tìm được CSV cũ (và kể cả tìm được, `cert_date` trong đó không đáng tin — xem đính
chính ở [A2-knx-crawler.md](A2-knx-crawler.md): `knx.org/devices` không hiển thị ngày chứng
nhận ở bất kỳ đâu). Thay vào đó: chạy [`scripts/crawl_knx_devices.py`](scripts/crawl_knx_devices.py)
(đã viết và test) để tự tạo baseline, output là CSV với cấu trúc **đã biết chính xác** (do
mình kiểm soát format, không phải đoán):

```
external_id,brand,model,source_url,crawled_at
allinbox-1612-v3,Zennio,ALLinBOX 1612 v3,https://www.knx.org/devices/allinbox-1612-v3,2026-08-13T01:54:20+00:00
```

Import thẳng, không cần bước "đoán cột" nữa:

1. Copy CSV vào staging table khớp đúng header:
   ```sql
   CREATE TEMP TABLE _staging_knx (
     external_id text,
     brand       text,
     model       text,
     source_url  text,
     crawled_at  timestamptz
   );
   ```
   ```
   \copy _staging_knx FROM 'knx_devices_baseline.csv' WITH (FORMAT csv, HEADER true)
   ```
2. Insert vào `registry.devices` — `category`, `device_type`, `cert_date` để NULL (không có
   nguồn ở v1, xem A2):
   ```sql
   INSERT INTO registry.devices (registry_key, external_id, brand, model, attributes)
   SELECT 'knx', external_id, brand, model,
          jsonb_build_object('source_url', source_url, 'crawled_at', crawled_at)
   FROM _staging_knx
   ON CONFLICT (registry_key, external_id) DO NOTHING;
   ```
3. Ghi snapshot baseline (thay `<N>` bằng số dòng thật đã crawl — script in ra số này khi
   chạy xong, không hardcode 10.195 nữa vì con số thật đổi theo thời điểm crawl):
   ```sql
   INSERT INTO registry.snapshots (registry_key, item_count, raw)
   SELECT 'knx', count(*), '{"source": "crawl_knx_devices.py", "note": "baseline v1"}'::jsonb
   FROM registry.devices WHERE registry_key = 'knx';
   ```

## Definition of Done

- [ ] `CREATE SCHEMA registry` chạy được trên Postgres 5433, không lỗi
- [ ] Rollback script tồn tại và test chạy được (drop rồi tạo lại không lỗi)
- [ ] `SELECT count(*) FROM registry.devices WHERE registry_key = 'knx'` ≈ 10.000+ (khớp số
      dòng crawler báo lúc chạy xong — con số thật đổi theo thời điểm, không cố định 10.195)
- [ ] `SELECT count(*) FROM registry.snapshots WHERE registry_key = 'knx'` = 1 (baseline)
- [ ] Chạy lại import script lần 2 không tạo duplicate (nhờ `ON CONFLICT DO NOTHING` +
      `UNIQUE (registry_key, external_id)`)
