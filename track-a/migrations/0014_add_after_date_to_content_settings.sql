-- Thêm mốc ngày lọc cho "Fetch toàn bộ" — chỉ lấy bài đăng sau ngày này (đọc ngay từ
-- listing page, xem migration 0013 + extract_articles.py --after-date). NULL = không lọc,
-- giữ hành vi cũ (chỉ giới hạn bởi full_fetch_max_pages).
ALTER TABLE news.content_settings ADD COLUMN full_fetch_after_date date;
