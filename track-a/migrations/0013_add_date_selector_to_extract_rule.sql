-- Đổi extract_rule của 12 nguồn html_list từ format cũ (list_selector chọn thẳng <a>) sang
-- format mới tách riêng card/link/date để lọc theo ngày được (--after-date ở
-- extract_articles.py) — verify thật từng site (2026-08-15), không suy đoán.
--
-- card_selector: chọn khối 1 bài (bao gồm cả link lẫn ngày)
-- link_selector: CSS tương đối trong card, tìm thẻ <a>
-- date_selector: CSS tương đối trong card, tìm phần tử chứa ngày
-- date_attr: nếu set (vd. "datetime"), đọc attribute đó thay vì text — dùng cho <time datetime="...">
--
-- 1 nguồn KHÔNG có date_selector: engadget-smart-home-reviews — ngày hiển thị dạng tương đối
-- ("2 months ago"), không parse ra ngày tuyệt đối được. Không ảnh hưởng nhiều vì nguồn này
-- cũng không có pagination thật (chỉ 2 bài, xem migration 0010).

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.l-post', 'link_selector', 'h2 a',
  'date_selector', 'time.post-date', 'date_attr', 'datetime',
  'page_url_template', extract_rule->'page_url_template'
)
WHERE slug IN ('the-ambient-news-matter', 'the-ambient-news-smart-home', 'the-ambient-reviews');

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'div.uael-post-wrapper', 'link_selector', 'h3 a',
  'date_selector', 'span.uael-post__date'
)
WHERE slug = 'aqara-blog';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.hentry.post', 'link_selector', 'a',
  'date_selector', 'p.entry-date',
  'page_url_template', extract_rule->'page_url_template'
)
WHERE slug = 'csa-iot-newsroom';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.article-block', 'link_selector', 'h3 a'
  -- KHÔNG có date_selector — .timestamp là ngày tương đối ("2 months ago"), không parse được
)
WHERE slug = 'engadget-smart-home-reviews';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.listing', 'link_selector', 'h1 a',
  'date_selector', 'time', 'date_attr', 'datetime',
  'page_url_template', extract_rule->'page_url_template'
)
WHERE slug = 'home-assistant-blog';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.post', 'link_selector', 'h2 a',
  'date_selector', 'span.published',
  'page_url_template', extract_rule->'page_url_template'
)
WHERE slug = 'matter-smarthome-de-development';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.post', 'link_selector', 'h2 a',
  'date_selector', 'span.published'
  -- không có page_url_template thật (trang 2 = 404, xem migration 0010)
)
WHERE slug = 'matter-smarthome-de-practice';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'div.featured_post, div.right', 'link_selector', 'div.post_title h4 a',
  'date_selector', 'div.time'
  -- không có page_url_template thật (trang 2 = 404, xem migration 0010)
)
WHERE slug = 'smartthings-blog-matter';

UPDATE news.sources SET extract_rule = jsonb_build_object(
  'card_selector', 'article.post', 'link_selector', 'h2 a',
  'date_selector', 'time.entry-time',
  'page_url_template', extract_rule->'page_url_template'
)
WHERE slug = 'staceyoniot-smart-home-tag';
