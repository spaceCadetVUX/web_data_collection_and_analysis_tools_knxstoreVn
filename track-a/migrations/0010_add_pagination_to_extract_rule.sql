-- Thêm extract_rule.page_url_template cho các nguồn html_list có thật nhiều hơn 1 trang —
-- verify trực tiếp (2026-08-14), không suy đoán: fetch trang 2 thật, so link với trang 1,
-- xác nhận khác nhau (không phải redirect ngược về trang 1) trước khi ghi vào đây.
--
-- {n} sẽ được thay bằng số trang (2, 3, 4...) khi extract_articles.py --max-pages > 1.
-- Trang 1 luôn là chính url gốc trong news.sources.url, KHÔNG cần page_url_template.
--
-- 3 nguồn html_list KHÔNG có page_url_template (giữ nguyên, cố tình không thêm):
--   - matter-smarthome-de-practice, smartthings-blog-matter: trang 2 trả 404 thật —
--     nội dung đã hết ở trang 1, không phải lỗi thiếu selector.
--   - engadget-smart-home-reviews: category chỉ có 2 bài, không có link "next page" nào.

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://www.aqara.com/en/blog/page/{n}/"}'::jsonb
WHERE slug = 'aqara-blog';

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://csa-iot.org/newsroom/page/{n}/"}'::jsonb
WHERE slug = 'csa-iot-newsroom';

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://matter-smarthome.de/en/development/page/{n}/"}'::jsonb
WHERE slug = 'matter-smarthome-de-development';

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://staceyoniot.com/tag/smart-home/page/{n}/"}'::jsonb
WHERE slug = 'staceyoniot-smart-home-tag';

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://www.the-ambient.com/news/matter/page/{n}/"}'::jsonb
WHERE slug = 'the-ambient-news-matter';

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://www.the-ambient.com/news/smart-home/page/{n}/"}'::jsonb
WHERE slug = 'the-ambient-news-smart-home';

UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://www.the-ambient.com/reviews/page/{n}/"}'::jsonb
WHERE slug = 'the-ambient-reviews';

-- Home Assistant dùng pattern riêng, KHÔNG phải /page/{n}/ (Jekyll blog, không phải WordPress)
UPDATE news.sources
SET extract_rule = extract_rule || '{"page_url_template": "https://www.home-assistant.io/blog/posts/{n}"}'::jsonb
WHERE slug = 'home-assistant-blog';
