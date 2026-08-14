-- Thêm crawl_mode để phân biệt full crawl (848 trang, quét toàn bộ registry) vs
-- incremental crawl (chỉ crawl tới khi gặp trang toàn thiết bị đã biết — phát hiện thiết
-- bị MỚI nhanh hơn nhiều, nhưng KHÔNG phát hiện được thiết bị bị gỡ khỏi registry).
--
-- Bắt buộc phải tách: anomaly-check ở import_and_diff.py so item_count với avg(item_count)
-- lịch sử — nếu trộn chung incremental (vài chục item) với full (~10.000 item) vào cùng 1
-- average, sẽ làm hỏng baseline dùng để phát hiện anomaly cho CẢ 2 loại crawl.

ALTER TABLE registry.crawl_log
  ADD COLUMN crawl_mode text NOT NULL DEFAULT 'full' CHECK (crawl_mode IN ('full', 'incremental'));
