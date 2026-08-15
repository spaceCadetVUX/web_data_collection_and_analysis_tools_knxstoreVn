-- docs/plan.md §4.1 có "CREATE INDEX ON news.articles (event_id)" nhưng migration 0009 bỏ
-- sót — B4 (event clustering) sẽ query nhiều theo event_id (gom bài cùng event, tìm bài
-- chưa gán event), thiếu index này sẽ full scan khi bảng lớn lên.
CREATE INDEX ON news.articles (event_id);
