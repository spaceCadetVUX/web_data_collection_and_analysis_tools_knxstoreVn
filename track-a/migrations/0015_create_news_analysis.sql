-- news.analysis (B3 — triage) theo schema docs/plan.md §4.1, ĐIỀU CHỈNH so với bản gốc:
--
-- - event_id: để plain uuid, KHÔNG FK tới news.events (bảng đó chưa tồn tại, xem B4) —
--   giống cách xử lý news.articles.event_id ở migration 0009.
-- - route: giữ nguyên CHECK ('batch','realtime','hard_rule') theo schema gốc, nhưng THỰC TẾ
--   dùng ở đây là 'realtime' qua CLI `claude -p` (subscription Claude Code, KHÔNG phải
--   Anthropic Messages API/Batch API tính phí token riêng) — quyết định 2026-08-15, xem
--   track-b/src/triage_articles.py. input_tokens/output_tokens sẽ NULL vì claude -p không
--   trả token count qua CLI thường.
-- - KHÔNG tạo news.batch_jobs — chỉ cần nếu dùng Batch API thật, không áp dụng ở đây.

CREATE TABLE news.analysis (
  id                 bigserial PRIMARY KEY,
  article_id         uuid REFERENCES news.articles(id) ON DELETE CASCADE,
  event_id           uuid,
  stage              text CHECK (stage IN ('triage', 'cluster', 'deep')),
  model              text NOT NULL,
  route              text CHECK (route IN ('batch', 'realtime', 'hard_rule')),
  verdict            text CHECK (verdict IN ('ignore', 'archive', 'digest', 'alert')),
  topics             text[],
  brands             text[],
  content_type       text,
  confidence         text CHECK (confidence IN ('low', 'medium', 'high')),
  summary_vi         text,
  why_it_matters     text,
  recommended_action text[],
  input_tokens       int,
  output_tokens      int,
  raw_response       jsonb,
  created_at         timestamptz DEFAULT now()
);
CREATE INDEX ON news.analysis (article_id);
CREATE INDEX ON news.analysis (event_id, stage);
