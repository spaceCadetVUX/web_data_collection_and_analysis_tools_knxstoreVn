-- news.articles + news.fetch_log + news.source_health — theo đúng schema docs/plan.md §4.1.
-- Dùng chung Postgres dev của Track A (registry-postgres, port 5433) — xem lý do ở
-- 0004_create_news_sources.sql. Đây là nơi lưu nội dung blog/content đã crawl (Track B),
-- tách biệt hoàn toàn với registry.devices (sản phẩm, Track A) dù chung 1 Postgres.

CREATE TABLE news.source_health (
  source_id             int PRIMARY KEY REFERENCES news.sources(id) ON DELETE CASCADE,
  last_attempt_at       timestamptz,
  last_success_at       timestamptz,
  consecutive_failures  int DEFAULT 0,
  items_last_7d         int DEFAULT 0,
  avg_items_per_week    numeric(6,2),
  last_error            text
);

CREATE TABLE news.fetch_log (
  id           bigserial PRIMARY KEY,
  source_id    int REFERENCES news.sources(id) ON DELETE CASCADE,
  fetched_at   timestamptz DEFAULT now(),
  http_status  int,
  item_count   int,
  new_count    int,
  duration_ms  int,
  error        text
);
CREATE INDEX ON news.fetch_log (source_id, fetched_at DESC);

CREATE TABLE news.articles (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       int REFERENCES news.sources(id),
  canonical_url   text UNIQUE NOT NULL,
  original_url    text,
  title           text,
  author          text,
  published_at    timestamptz,                 -- từ nguồn, KHÔNG tin cậy
  first_seen_at   timestamptz DEFAULT now(),   -- dùng cái này để sort
  lang            text,
  body_text       text,
  word_count      int,
  simhash         bigint,
  simhash_b0      int, simhash_b1 int,         -- 4 band 16-bit để index (dùng ở B2, chưa dùng ở B1)
  simhash_b2      int, simhash_b3 int,
  extract_status  text DEFAULT 'ok'
                  CHECK (extract_status IN ('ok','partial','failed','js_required')),
  event_id        uuid,                        -- FK tới news.events, thêm khi build B4
  created_at      timestamptz DEFAULT now()
);
CREATE INDEX ON news.articles (simhash_b0);
CREATE INDEX ON news.articles (simhash_b1);
CREATE INDEX ON news.articles (simhash_b2);
CREATE INDEX ON news.articles (simhash_b3);
CREATE INDEX ON news.articles (first_seen_at DESC);
CREATE INDEX ON news.articles (source_id);
