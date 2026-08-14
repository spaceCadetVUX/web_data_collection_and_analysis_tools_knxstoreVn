-- Bổ sung extract_rule.list_selector cho 12 nguồn kind=html_list trong news.sources —
-- trước migration này extract_rule rỗng ({}), B1 (news-extractor, chưa build) sẽ không
-- bóc tách được danh sách bài từ các trang chuyên mục này (chỉ parse như 1 bài, sai).
--
-- Verify bằng cách tải trực tiếp HTML từng trang (2026-08-14) + BeautifulSoup, KHÔNG suy
-- đoán — mỗi selector đã test khớp đúng số bài + href thật trên bản HTML tải về. Riêng
-- androidcentral-smart-home: card bài viết không có <a href> nào trong static HTML (nav
-- vào bài xử lý qua JS phía client) — đánh dấu requires_js=true, cần news-renderer (B6)
-- thay vì trafilatura thường; selector ghi lại là best-effort, cần xác nhận lại khi B6 build.

UPDATE news.sources SET extract_rule = '{"list_selector": "article.l-post h2 a"}'::jsonb
  WHERE slug IN ('the-ambient-news-matter', 'the-ambient-news-smart-home', 'the-ambient-reviews');

UPDATE news.sources SET extract_rule = '{"list_selector": "div.uael-post-wrapper h3 a"}'::jsonb
  WHERE slug = 'aqara-blog';

UPDATE news.sources SET extract_rule = '{"list_selector": "article.hentry.post h3.entry-title a"}'::jsonb
  WHERE slug = 'csa-iot-newsroom';

UPDATE news.sources SET extract_rule = '{"list_selector": "article.article-block h3 a"}'::jsonb
  WHERE slug = 'engadget-smart-home-reviews';

UPDATE news.sources SET extract_rule = '{"list_selector": "article.listing h1 a"}'::jsonb
  WHERE slug = 'home-assistant-blog';

UPDATE news.sources SET extract_rule = '{"list_selector": "article.post h2 a"}'::jsonb
  WHERE slug IN ('matter-smarthome-de-development', 'matter-smarthome-de-practice', 'staceyoniot-smart-home-tag');

UPDATE news.sources SET extract_rule = '{"list_selector": "div.post_title h4 a"}'::jsonb
  WHERE slug = 'smartthings-blog-matter';

UPDATE news.sources SET extract_rule = '{"list_selector": "article.search-result"}'::jsonb,
                         requires_js = true,
                         notes = notes || ' — LƯU Ý: card không có <a href> trong static HTML, cần Playwright (B6) để lấy link thật, selector chưa verify qua JS-rendered DOM.'
  WHERE slug = 'androidcentral-smart-home';
