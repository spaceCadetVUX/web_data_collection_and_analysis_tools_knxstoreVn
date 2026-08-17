-- Lịch tự động cho Track B (content/blog) — chạy mode='latest' (rẻ, tối đa 3 bài mới/nguồn)
-- theo cadence HÀNG NGÀY, khớp docs/plan.md §Track B (khác registry.app_settings bên Track A:
-- hàng tuần + luôn full). Chỉ giờ:phút, không có thứ (daily, không phải weekly).
--
-- schedule_enabled mặc định false — không tự chạy gì cho tới khi người dùng bật ở Settings,
-- tránh crawl 36 nguồn ngay sau khi migration này chạy trên máy nào đó.

ALTER TABLE news.content_settings
  ADD COLUMN schedule_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN schedule_hour    smallint NOT NULL DEFAULT 7 CHECK (schedule_hour BETWEEN 0 AND 23),
  ADD COLUMN schedule_minute  smallint NOT NULL DEFAULT 30 CHECK (schedule_minute BETWEEN 0 AND 59);
