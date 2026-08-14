-- Schema `news` cho Track B (News Pipeline) — bảng news.sources theo docs/plan.md §4.1.
-- Dùng chung Postgres dev của Track A (registry-postgres, port 5433) để quản lý qua UI
-- Settings có sẵn (track-a/webapp/) thay vì dựng webapp riêng cho Track B lúc này.
--
-- Khác với schema gốc trong plan.md: thêm UNIQUE(url) — cần để form "Thêm nguồn" dùng
-- ON CONFLICT (url) DO NOTHING mà không tạo bản ghi trùng khi nhập lại 1 URL.

CREATE SCHEMA IF NOT EXISTS news;

CREATE TABLE news.sources (
  id            serial PRIMARY KEY,
  slug          text UNIQUE NOT NULL,
  name          text NOT NULL,
  kind          text NOT NULL
                CHECK (kind IN ('rss','atom','sitemap','json_api',
                                'html_list','search_query','registry','manual')),
  url           text UNIQUE,
  extract_rule  jsonb DEFAULT '{}'::jsonb,
  lang          text,
  region        text,
  category      text
                CHECK (category IN ('standard_body','manufacturer','registry',
                                    'media','community','social','distributor')),
  tier          smallint DEFAULT 2 CHECK (tier BETWEEN 1 AND 3),
  fetch_cron    text DEFAULT '0 */6 * * *',
  requires_js   boolean DEFAULT false,
  enabled       boolean DEFAULT true,
  notes         text,
  created_at    timestamptz DEFAULT now()
);
