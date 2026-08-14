-- Setting cho Track B webapp: số trang listing tối đa được lật khi bấm "Fetch toàn bộ"
-- (xem migration 0010 — chỉ áp dụng cho nguồn có extract_rule.page_url_template, nguồn
-- không có thì luôn chỉ 1 trang thật bất kể setting này). Giống registry.app_settings bên
-- Track A (1 dòng duy nhất, sửa qua UI Settings/Content).

CREATE TABLE news.content_settings (
  id                    smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  full_fetch_max_pages  int NOT NULL DEFAULT 5 CHECK (full_fetch_max_pages BETWEEN 1 AND 50),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

INSERT INTO news.content_settings (id, full_fetch_max_pages) VALUES (1, 5)
ON CONFLICT (id) DO NOTHING;
