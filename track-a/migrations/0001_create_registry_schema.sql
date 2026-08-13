-- Track A — schema `registry`
-- Xem track-a/A1-schema-import.md và knx-news-agent-plan.md §4.3 để biết bối cảnh.
-- CHƯA TEST trên Postgres 5433 thật — chưa có credential (xem track-a/00-overview.md, câu hỏi #5).
-- Chạy bằng: psql "$DATABASE_URL" -f 0001_create_registry_schema.sql

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

-- Dùng chung cho Track A (diff) và Track B (hard rule, ranking) — xem
-- knx-news-agent-plan.md §4.1 phần ghi chú deviation.
CREATE TABLE registry.brands_of_interest (
  id         serial PRIMARY KEY,
  brand      text UNIQUE NOT NULL,
  aliases    text[],
  aliases_zh text[],
  priority   smallint DEFAULT 2,
  is_active  boolean DEFAULT true
);

CREATE TABLE registry.crawl_log (
  id            bigserial PRIMARY KEY,
  registry_key  text NOT NULL,
  run_at        timestamptz DEFAULT now(),
  item_count    int,
  new_count     int,
  removed_count int,
  status        text,        -- ok | failed | aborted_anomaly
  error         text,
  duration_ms   int
);
CREATE INDEX ON registry.crawl_log (registry_key, run_at DESC);
