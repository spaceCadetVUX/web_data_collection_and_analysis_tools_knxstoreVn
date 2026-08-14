# KNX News Intelligence Agent

**Bản kế hoạch triển khai v1.1**
Chủ dự án: Tùng (KNXStore.vn)
Ngày lập: 08/08/2026
Thay đổi so với v1.0: bỏ toàn bộ LLM local, chuyển sang Claude Haiku 4.5 API cho cả 2 tầng. Bỏ vector embedding ở giai đoạn 0.
Trạng thái: Draft để review với team dev nội bộ

---

## 1. Mục tiêu và phạm vi

### 1.1 Mục tiêu

Thu thập, lọc và tổng hợp thông tin ngành building automation phục vụ 2 nhóm quyết định:

| Nhóm | Câu hỏi cần trả lời | Người dùng |
|---|---|---|
| Sản phẩm và phân phối | Hãng nào ra sản phẩm mới? Tiêu chuẩn nào thay đổi? Có recall hay EOL không? | Tùng |
| Nội dung và marketing | Chủ đề nào đang có nhu cầu? Angle nào chuyển thể được sang thị trường VN? | Tùng, Vũ |

### 1.2 Ngoài phạm vi giai đoạn này

- Dashboard web (FastAPI/React)
- MCP server expose ra Claude
- Vector embedding và semantic search
- Auto-publish nội dung
- Bất kỳ hạ tầng VPS mới nào

Các mục trên chỉ mở khi đạt tiêu chí Go ở mục 10.

### 1.3 Nguyên tắc thiết kế

1. **Tái sử dụng hạ tầng hiện có.** Không dựng stack Docker Compose mới, không thêm VPS.
2. **Registry diff trước, news crawl sau.** Dữ liệu chứng nhận là leading indicator, độ nhiễu gần 0.
3. **Phân loại rời rạc, không dùng score.** LLM scoring không calibrate được.
4. **Feedback loop từ ngày đầu.** Không có nó thì sau 3 tuần prompt không cải thiện được.
5. **Nhóm bài theo sự kiện, không theo bài.** Một product release xuất hiện trên 5 nguồn trong 48h.
6. **Không tối ưu sớm.** Ở volume 40 đến 80 bài/ngày, giải pháp đơn giản luôn thắng giải pháp đúng về lý thuyết.

---

## 2. Kiến trúc

**Cập nhật (2026-08-14): bỏ n8n khỏi kiến trúc Track B.** Quyết định giống Track A (xem
`track-a/README.md` mục 0, A5 đã đổi từ n8n sang webapp riêng) — không phụ thuộc n8n
production (`n8n.tungvu.vn`) mà nhóm không có quyền truy cập lúc build, và tránh phải học
n8n để dựng workflow. Trigger chạy pipeline (fetch nguồn, chạy digest...) qua **UI webapp**
(nút bấm, giống Dashboard Track A) hoặc **trực tiếp qua Claude/MCP connector** (gọi tay khi
cần) — không cần orchestrator cron riêng ở giai đoạn này. Mọi chỗ nhắc "n8n" bên dưới trong
tài liệu này (sơ đồ luồng, task B1, OrbStack networking, marketing bắt link) đã lỗi thời so
với quyết định này, xem ghi chú tại từng chỗ.

### 2.1 Thành phần

| Lớp | Công nghệ | Trạng thái |
|---|---|---|
| Orchestrator | ~~n8n~~ — Webapp (FastAPI, giống `track-a/webapp/`) + trigger tay qua Claude/MCP connector | **Cần viết**, không dùng n8n |
| Storage | PostgreSQL pgvector:pg17, port 5433 | Đã có, thêm 3 schema mới |
| Extract | Container `news-extractor` (FastAPI + trafilatura) | **Cần viết** |
| Render fallback | Container `news-renderer` (Playwright) | **Cần viết**, chỉ khi cần |
| Triage LLM | Claude Haiku 4.5 qua Batch API | Cần API key |
| Deep analysis LLM | Claude Haiku 4.5 qua Messages API | Cùng key |
| Event clustering | Claude Haiku 4.5, 1 call/ngày | Xem 5.4 |
| Delivery | Zalo KHub MCP, Telegram Bot | KHub đã có, Telegram cần tạo bot |
| WeChat bridge | Wechat2RSS self-host | **Cần dựng** |

**Không dùng Ollama.** Quyết định này loại bỏ được: quản lý RAM cho model 8B, cấu hình network container tới host, độ trễ swap model, và rủi ro chất lượng của model 8B với tiếng Trung.

Container mới: 2 bắt buộc (`news-extractor`, `wechat2rss`) + 1 tùy chọn (`news-renderer`).

### 2.2 Sơ đồ luồng

```
                    ┌─────────────────┐
                    │  news.sources   │
                    └────────┬────────┘
                             │ trigger tay (UI webapp / Claude connector) —
                             │ KHÔNG qua n8n, xem ghi chú đầu mục 2
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        RSS/Atom        Sitemap        HTML list
              └──────────────┼──────────────┘
                             ▼
                  ┌──────────────────────┐
                  │  news-extractor      │  POST /extract
                  │  trafilatura         │  → title, body, lang,
                  │  fallback readability│    canonical_url, pub_at
                  └──────────┬───────────┘
                             │ requires_js=true
                             ├────────► news-renderer (Playwright)
                             ▼
              ┌──────────────────────────────┐
              │  DEDUPE 2 TẦNG               │
              │  1. canonical URL            │
              │  2. SimHash (Hamming ≤ 3)    │
              └──────────┬───────────────────┘
                         ▼ (bài mới)
              ┌──────────────────────────────┐
              │  TẦNG 1: TRIAGE              │
              │  Haiku 4.5 qua Batch API     │
              │  → verdict enum              │
              │  (bypass batch nếu hard rule)│
              └──────────┬───────────────────┘
                         ▼
              ┌──────────────────────────────┐
              │  EVENT CLUSTERING            │
              │  Haiku 4.5, 1 call/ngày      │
              │  input = toàn bộ title 72h   │
              └──────────┬───────────────────┘
                         ▼ event có verdict ∈ {digest, alert}
              ┌──────────────────────────────┐
              │  TẦNG 2: DEEP ANALYSIS       │
              │  Haiku 4.5, input = event    │
              └──────────┬───────────────────┘
                         ▼
              ┌──────────────────────────────┐
              │  RANKING + DELIVERY          │
              │  top 5 event/ngày → digest   │
              │  alert → gửi ngay            │
              └──────────┬───────────────────┘
                         ▼
                  Zalo KHub / Telegram
                         │
                         ▼
                  news.feedback (useful/noise)
```

### 2.3 Track song song: Registry Diff

Độc lập với news pipeline, ưu tiên cao hơn, không dùng LLM.

```
KNX certified DB (10,195 devices, đã scrape)
CSA Matter certified DB
DALI Alliance product DB
        │
        ▼ crawl lại hàng tuần
   diff vs snapshot tuần trước
        │
        ▼ device mới / thay đổi
   filter theo brands_of_interest
        │
        ▼
   alert trực tiếp, KHÔNG qua LLM
```

Sớm hơn press release từ 2 đến 8 tuần. Độ chính xác 100%.

---

## 3. Chi phí vận hành

### 3.1 Đơn giá tham chiếu

Claude Haiku 4.5, model ID `claude-haiku-4-5-20251001`, tại 08/2026:

| Loại | Giá / 1M token |
|---|---|
| Input standard | $1.00 |
| Output standard | $5.00 |
| Input qua Batch API | $0.50 |
| Output qua Batch API | $2.50 |
| Cache hit | $0.10 (10% base input) |
| Cache write 5 phút | $1.25 (1.25x) |
| Cache write 1 giờ | $2.00 (2x) |

Context window Haiku 4.5: 200K token. Đủ thoải mái cho mọi call trong hệ thống này.

**Cần verify lại trước khi chốt ngân sách:** giá thay đổi theo thời gian, kiểm tra tại https://docs.claude.com trước khi trình duyệt chi phí.

### 3.2 Ước tính theo giả định volume

Giả định: 40 nguồn, 60 bài/ngày sau dedupe URL, 12 event/ngày qua tầng 2.

| Tầng | Token/ngày | Token/tháng | Chi phí/tháng |
|---|---|---|---|
| Tầng 1 triage (batch) | 120K in + 9K out | 3.6M in + 270K out | $2.48 |
| Event clustering | 3K in + 1.5K out | 90K in + 45K out | $0.20 |
| Tầng 2 deep | 48K in + 6K out | 1.44M in + 180K out | $2.34 |
| **Tổng** | | | **~$5/tháng** |

Kịch bản volume gấp 3 (180 bài/ngày): vẫn dưới $20/tháng.

**Kết luận: chi phí API không phải yếu tố ràng buộc.** Quyết định bỏ local là đúng về mặt kinh tế. Ràng buộc thật là thời gian dev và khả năng duy trì thói quen đọc digest.

### 3.3 Tối ưu chi phí

Chỉ áp dụng nếu volume vượt 200 bài/ngày. Ở mức hiện tại, tối ưu chi phí là lãng phí thời gian dev:

- **Batch API** cho tầng 1: giảm 50%, đánh đổi bằng độ trễ tối đa 24h. Chấp nhận được vì digest chạy 1 lần/ngày.
- **Prompt caching** cho system prompt tầng 1 (taxonomy + brands_of_interest, khoảng 1500 token cố định). Chỉ hiệu quả nếu request đi liên tục trong cửa sổ cache 5 phút.
- **Truncate input:** tầng 1 chỉ cần title + 1200 từ đầu body. Không gửi cả bài. Đây là đòn bẩy lớn nhất và nên làm ngay từ đầu.

### 3.4 Luồng realtime vs batch

Không phải mọi bài đều chờ được 24h:

| Điều kiện | Luồng | Độ trễ |
|---|---|---|
| Nguồn tier 1 AND brand ∈ brands_of_interest | Messages API realtime | < 1 phút |
| Registry diff phát hiện device mới | Không qua LLM, alert thẳng | < 1 phút |
| Còn lại | Batch API | Tối đa 24h |

---

## 4. Data model

### 4.1 Schema `news`

```sql
CREATE SCHEMA IF NOT EXISTS news;

-- ============ NGUỒN ============
CREATE TABLE news.sources (
  id            serial PRIMARY KEY,
  slug          text UNIQUE NOT NULL,
  name          text NOT NULL,
  kind          text NOT NULL
                CHECK (kind IN ('rss','atom','sitemap','json_api',
                                'html_list','search_query','registry','manual')),
  url           text,
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

-- ============ SỨC KHỎE NGUỒN ============
CREATE TABLE news.source_health (
  source_id             int PRIMARY KEY REFERENCES news.sources(id) ON DELETE CASCADE,
  last_attempt_at       timestamptz,
  last_success_at       timestamptz,
  consecutive_failures  int DEFAULT 0,
  items_last_7d         int DEFAULT 0,
  avg_items_per_week    numeric(6,2),
  last_error            text
);

CREATE TABLE news.fetch_log (
  id           bigserial PRIMARY KEY,
  source_id    int REFERENCES news.sources(id) ON DELETE CASCADE,
  fetched_at   timestamptz DEFAULT now(),
  http_status  int,
  item_count   int,
  new_count    int,
  duration_ms  int,
  error        text
);
CREATE INDEX ON news.fetch_log (source_id, fetched_at DESC);

-- ============ SỰ KIỆN ============
CREATE TABLE news.events (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title_canonical    text,
  first_seen_at      timestamptz DEFAULT now(),
  last_updated_at    timestamptz DEFAULT now(),
  article_count      int DEFAULT 1,
  source_count       int DEFAULT 1,
  primary_article_id uuid
);
CREATE INDEX ON news.events (last_updated_at DESC);

-- ============ BÀI VIẾT ============
CREATE TABLE news.articles (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       int REFERENCES news.sources(id),
  canonical_url   text UNIQUE NOT NULL,
  original_url    text,
  title           text,
  author          text,
  published_at    timestamptz,                 -- từ nguồn, KHÔNG tin cậy
  first_seen_at   timestamptz DEFAULT now(),   -- dùng cái này để sort
  lang            text,
  body_text       text,
  word_count      int,
  simhash         bigint,
  simhash_b0      int, simhash_b1 int,         -- 4 band 16-bit để index
  simhash_b2      int, simhash_b3 int,
  extract_status  text DEFAULT 'ok'
                  CHECK (extract_status IN ('ok','partial','failed','js_required')),
  event_id        uuid REFERENCES news.events(id),
  created_at      timestamptz DEFAULT now()
);
CREATE INDEX ON news.articles (simhash_b0);
CREATE INDEX ON news.articles (simhash_b1);
CREATE INDEX ON news.articles (simhash_b2);
CREATE INDEX ON news.articles (simhash_b3);
CREATE INDEX ON news.articles (first_seen_at DESC);
CREATE INDEX ON news.articles (event_id);

-- Chừa chỗ cho embedding giai đoạn sau, chưa dùng ở v1.1:
-- ALTER TABLE news.articles ADD COLUMN embedding vector(1024);

-- ============ PHÂN TÍCH AI ============
CREATE TABLE news.analysis (
  id                 bigserial PRIMARY KEY,
  article_id         uuid REFERENCES news.articles(id) ON DELETE CASCADE,
  event_id           uuid REFERENCES news.events(id) ON DELETE CASCADE,
  stage              text CHECK (stage IN ('triage','cluster','deep')),
  model              text NOT NULL,        -- ghi rõ model ID để so sánh về sau
  route              text CHECK (route IN ('batch','realtime','hard_rule')),
  verdict            text CHECK (verdict IN ('ignore','archive','digest','alert')),
  topics             text[],
  brands             text[],
  content_type       text,
  confidence         text CHECK (confidence IN ('low','medium','high')),
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

-- ============ THEO DÕI BATCH JOB ============
CREATE TABLE news.batch_jobs (
  id            bigserial PRIMARY KEY,
  batch_id      text UNIQUE,          -- ID trả về từ Batch API
  submitted_at  timestamptz DEFAULT now(),
  completed_at  timestamptz,
  status        text,                 -- submitted | in_progress | ended | failed
  request_count int,
  result_count  int,
  error         text
);

-- ============ DIGEST ============
CREATE TABLE news.digests (
  id           bigserial PRIMARY KEY,
  sent_at      timestamptz DEFAULT now(),
  channel      text,                  -- zalo_khub | telegram
  kind         text,                  -- daily | alert | weekly
  period_start timestamptz,
  period_end   timestamptz,
  item_count   int,
  payload      jsonb
);

-- ============ FEEDBACK ============
CREATE TABLE news.feedback (
  id         bigserial PRIMARY KEY,
  event_id   uuid REFERENCES news.events(id) ON DELETE CASCADE,
  digest_id  bigint REFERENCES news.digests(id),
  user_name  text,
  rating     smallint CHECK (rating IN (-1, 0, 1, 2)),
                       -- -1 noise | 0 neutral | 1 useful | 2 đã hành động
  note       text,
  created_at timestamptz DEFAULT now()
);

```

**`brands_of_interest` chuyển sang schema `registry`** (xem §4.3) — bảng này được dùng ở cả
Track A (registry diff) lẫn Track B (hard rule §6.2, ranking §6.4), và Track A build trước,
độc lập với `news`. Đặt ở `registry` để Track A không phụ thuộc ngược vào schema `news` chưa
tồn tại. Track B tham chiếu thẳng `registry.brands_of_interest`, không định nghĩa lại.

### 4.2 Schema `marketing`

```sql
CREATE SCHEMA IF NOT EXISTS marketing;

CREATE TABLE marketing.inspiration (
  id               bigserial PRIMARY KEY,
  platform         text,   -- xiaohongshu | wechat | douyin | instagram | tiktok
  post_url         text,
  captured_at      timestamptz DEFAULT now(),
  captured_by      text,
  engagement       jsonb,
  hook_type        text,   -- pain_point | before_after | listicle |
                           -- myth_bust | cost_breakdown | fail_story
  visual_format    text,
  original_angle   text,
  adapted_angle_vi text,
  target_segment   text,   -- homeowner | interior_designer | electrician | si
  status           text DEFAULT 'idea'
                   CHECK (status IN ('idea','briefed','produced','published','dropped')),
  notes            text
);
```

### 4.3 Schema `registry`

```sql
CREATE SCHEMA IF NOT EXISTS registry;

CREATE TABLE registry.snapshots (
  id           bigserial PRIMARY KEY,
  registry_key text,        -- knx | matter_csa | dali
  taken_at     timestamptz DEFAULT now(),
  item_count   int,
  raw          jsonb
);

CREATE TABLE registry.devices (
  id            bigserial PRIMARY KEY,
  registry_key  text,
  external_id   text,
  brand         text,
  model         text,
  category      text,
  device_type   text,
  cert_date     date,
  attributes    jsonb,
  first_seen_at timestamptz DEFAULT now(),
  last_seen_at  timestamptz DEFAULT now(),
  status        text DEFAULT 'active',   -- active | removed
  UNIQUE (registry_key, external_id)
);
CREATE INDEX ON registry.devices (brand);
CREATE INDEX ON registry.devices (first_seen_at DESC);

-- ============ BRAND QUAN TÂM ============
-- Dùng chung cho Track A (diff) và Track B (hard rule §6.2, ranking §6.4)
CREATE TABLE registry.brands_of_interest (
  id         serial PRIMARY KEY,
  brand      text UNIQUE NOT NULL,
  aliases    text[],        -- ['ABB','ABB i-bus','Busch-Jaeger']
  aliases_zh text[],        -- tên tiếng Trung, bắt buộc cho nguồn CN
  priority   smallint DEFAULT 2,
  is_active  boolean DEFAULT true
);

-- ============ LỊCH SỬ CRAWL ============
-- Vai trò tương đương news.fetch_log nhưng cho registry crawler (KNX, CSA Matter, DALI)
CREATE TABLE registry.crawl_log (
  id            bigserial PRIMARY KEY,
  registry_key  text NOT NULL,
  run_at        timestamptz DEFAULT now(),
  item_count    int,
  new_count     int,
  removed_count int,
  status        text,        -- ok | failed | aborted_anomaly
  error         text,
  duration_ms   int
);
CREATE INDEX ON registry.crawl_log (registry_key, run_at DESC);
```

---

## 5. Xử lý trùng lặp và gom sự kiện

**Content hash SHA256 gần như vô dụng.** Timestamp động, block related articles, cookie banner, ad slot, view counter làm hash đổi mỗi lần crawl. Chỉ bắt được trùng lặp byte-identical, tức gần như không bao giờ.

### 5.1 Tầng 1: Canonical URL

Strip các tham số sau, gồm cả biến thể của site TQ và WeChat:

```
utm_*, fbclid, gclid, msclkid, ref, referrer,
spm, from, isappinstalled, scene, chksm, sn, srcid,
sharer_*, mkt_tok, _ga, yclid
```

Thêm: lowercase host, bỏ trailing slash, bỏ fragment, resolve chuỗi redirect 301/302, ưu tiên thẻ `<link rel="canonical">` nếu có.

### 5.2 Tầng 2: SimHash

64-bit trên `body_text` sau khi strip boilerplate. Ngưỡng Hamming distance ≤ 3.

**Kỹ thuật index:** Postgres không có toán tử Hamming nhanh. Chia simhash thành 4 band 16-bit, index riêng từng band. Candidate = trùng ít nhất 1 band (pigeonhole principle với d ≤ 3), sau đó tính Hamming chính xác trên tập candidate. Đây là lý do có 4 cột `simhash_b0..b3`.

### 5.3 Quyết định bỏ vector embedding ở giai đoạn 0

Anthropic không cung cấp embedding API. Nếu giữ vector clustering thì phải thêm 1 trong 3:

| Phương án | Ưu | Nhược |
|---|---|---|
| Voyage AI (partner của Anthropic) | Chất lượng tốt, multilingual | Thêm vendor, thêm API key, thêm chi phí |
| Ollama `bge-m3` local | Miễn phí, chỉ 2 đến 2.5GB RAM | Mâu thuẫn với quyết định bỏ local |
| Cohere / OpenAI embeddings | Sẵn có | Thêm vendor ngoài hệ Anthropic |

**Quyết định: bỏ embedding, dùng LLM để gom sự kiện.** Ở volume 60 bài/ngày, một call Haiku với toàn bộ title trong cửa sổ 72h giải quyết được bài toán clustering mà không cần vector store, không cần calibrate ngưỡng cosine, không cần thêm vendor.

Cột `embedding` để lại dạng comment trong schema, bật khi mở scope semantic search.

### 5.4 Event clustering bằng LLM

1 call/ngày, sau khi tầng 1 xong:

- Input: danh sách `{article_id, title, source, first_seen_at}` của toàn bộ bài trong 72h chưa gán event. Ước 150 đến 200 bài × 25 token ≈ 5K token.
- Output: mảng nhóm, mỗi nhóm gồm `article_ids[]` và `title_canonical`.
- Ghi vào `news.events`, cập nhật `article_count` và `source_count`.

Ràng buộc trong prompt: chỉ gom khi cùng **một sự kiện cụ thể** (cùng sản phẩm, cùng thông báo), không gom theo chủ đề chung. Đây là lỗi thường gặp: LLM có xu hướng gom mọi bài về KNX vào một nhóm.

Cần test trên tập 100 bài có nhãn thủ công trước khi đưa vào production.

---

## 6. Tầng AI

### 6.1 Tầng 1: Triage

Model: Haiku 4.5. Route mặc định Batch API, bypass sang realtime theo bảng 3.4.

Input: `title` + 1200 từ đầu `body_text` + tên nguồn. Output JSON strict, **không có score**:

```json
{
  "keep": true,
  "verdict": "digest",
  "topics": ["KNX", "lighting_control"],
  "brands": ["ABB"],
  "content_type": "product_release",
  "confidence": "high"
}
```

`verdict` enum: `ignore` | `archive` | `digest` | `alert`

`content_type` enum: `product_release` | `standard_update` | `recall` | `eol` | `acquisition` | `price_change` | `tender` | `case_study` | `opinion` | `other`

**Lý do bỏ scoring 0 đến 100:** LLM scoring không calibrate. Cùng một bài chạy 2 lần lệch 10 đến 15 điểm. Thiết kế 4 ngưỡng trên thang float không ổn định sẽ tạo hành vi ngẫu nhiên ở biên.

System prompt cố định (taxonomy + `brands_of_interest` + few-shot) ước 1500 token, là ứng viên cho prompt caching nếu volume tăng.

### 6.2 Hard rule bypass LLM

Chuyển thẳng `alert`, không cần LLM quyết:

```
brand ∈ brands_of_interest AND content_type ∈ {recall, eol, standard_update}
registry_diff phát hiện device mới của brand ∈ brands_of_interest
```

### 6.3 Tầng 2: Deep analysis

Model: Haiku 4.5, Messages API realtime. Chạy trên **event**, không phải article. Điều kiện: event có ít nhất 1 article verdict ∈ {digest, alert}. Input: gộp 2 đến 3 bài đại diện trong event.

```json
{
  "summary_vi": "2 đến 3 câu, giữ nguyên thuật ngữ kỹ thuật tiếng Anh",
  "why_it_matters": "1 đến 2 câu, góc nhìn nhà phân phối tại VN",
  "recommended_action": [
    "Xin datasheet từ đại diện khu vực",
    "Kiểm tra tồn kho dòng tương đương",
    "Cân nhắc bài blog kỹ thuật"
  ]
}
```

### 6.4 Ranking cho digest

Không dùng output LLM làm sort key chính:

```
rank_score =
    tier_weight          (tier 1 = 3, tier 2 = 2, tier 3 = 1)
  + source_count × 2     (số nguồn độc lập trong event)
  + brand_match × 5      (brand ∈ brands_of_interest)
  + type_weight          (recall=5, standard_update=4, product_release=3,
                          price_change=3, acquisition=2, còn lại=1)
```

Lấy top 5 event mỗi ngày. Dựa trên tín hiệu quan sát được, không phải phán đoán của LLM.

### 6.5 Kỷ luật vận hành LLM

- Ghi `model` ID đầy đủ vào mọi record `news.analysis`. Khi đổi model, so sánh được kết quả trước sau.
- Ghi `input_tokens` và `output_tokens` để theo dõi chi phí thực tế so với ước tính ở 3.2.
- Prompt lưu trong git dưới `prompts/`, không hardcode trong n8n node. Mỗi lần sửa prompt là 1 commit.
- JSON parse fail thì retry 1 lần với temperature 0, sau đó ghi `verdict = 'archive'` và log lại. Không để pipeline dừng.
- **Event clustering fail toàn bộ (không phải per-article, vì đây là 1 call/ngày cho cả batch):** retry 1 lần. Nếu vẫn fail, gửi digest không group (mỗi article đứng riêng, `event_id = null`) — không được để mất digest cả ngày hôm đó. Log lỗi để theo dõi tần suất fail của call này riêng biệt.

---

## 7. Nguồn dữ liệu

**Cập nhật (2026-08-13):** Tùng đang tự tìm nguồn uy tín để crawl bài viết cho Track B, thay
vì dùng nguyên danh sách mẫu ở §7.2 — sẽ đưa vào `sources.yaml` khi build B0. Danh sách §7.2
dưới đây vẫn là tham khảo cho cơ cấu tier/category, không phải danh sách chốt cuối.

### 7.1 Cách quản lý

Seed bằng `sources.yaml` trong git, load vào DB qua migration script. Runtime đọc từ DB để bật/tắt không cần deploy.

```yaml
- slug: knx-association-news
  name: KNX Association News
  kind: rss
  url: https://www.knx.org/knx-en/for-professionals/News/index.php
  lang: en
  region: GLOBAL
  category: standard_body
  tier: 1
  fetch_cron: "0 8 * * *"

- slug: qianjia-smartbuilding
  name: 千家网 智能建筑
  kind: html_list
  url: https://www.qianjia.com/
  extract_rule:
    list_selector: ".news-list li a"
    date_selector: ".time"
  lang: zh
  region: CN
  category: media
  tier: 2
```

### 7.2 Phân bổ nguồn mục tiêu

| Nhóm | Số nguồn | Tier | Ghi chú |
|---|---|---|---|
| Registry (KNX, CSA Matter, DALI) | 3 | 1 | Ưu tiên cao nhất |
| Standard body (KNX Assoc, DALI Alliance, CSA, BACnet Intl) | 4 | 1 | RSS ổn định |
| Hãng EU/global (ABB, Schneider, Siemens, JUNG, Gira, Zennio, Theben) | 7 | 1 | Đa số có RSS hoặc sitemap |
| Hãng TQ (GVS 视声, HDL 河东, Moorgen, Tuya, Aqara) | 5 | 2 | Chủ yếu html_list |
| Media TQ (千家网, 中国安防展览网, CSHIA) | 3 | 2 | Nguồn tin sản phẩm sớm |
| WeChat 公众号 qua Wechat2RSS | 10 đến 15 | 2 | Xem 7.3 |
| Media EU/US (LEDs Magazine, Lux Review, KNX Journal) | 3 | 2 | |
| Google News search query | 4 | 3 | 2 query EN, 2 query ZH |
| Manual | 1 | 1 | Kênh đẩy link từ Zalo |

Tổng khoảng 40 nguồn. Không tham hơn ở giai đoạn đầu.

Mẫu search query cho nguồn TQ mà không cần crawl:

```
https://news.google.com/rss/search
  ?q=KNX+智能照明+when:7d
  &hl=zh-CN&gl=CN&ceid=CN:zh-Hans
```

### 7.3 WeChat 公众号

Tình trạng công cụ tại 08/2026:

| Giải pháp | Đánh giá | Quyết định |
|---|---|---|
| Wechat2RSS (ttttmr) | Self-host được, delay trung bình 6h, còn maintain | **Chọn** |
| WeWe RSS | Đã archive 19/01/2026, còn chạy nhưng không maintain | Loại |
| RSSHub route wechat | Cần gateway riêng, hay hỏng | Loại |
| Sogou Weixin | Captcha nặng | Loại |

**Cảnh báo vận hành:** dùng tài khoản WeChat phụ, không dùng tài khoản cá nhân của Tùng. Có rủi ro hạn chế tài khoản.

### 7.4 Xiaohongshu

**Quyết định: không tự crawl.** Cơ sở kỹ thuật tại 2026:

- Chữ ký `x-s` phải sinh realtime theo URL, timestamp và trường `a1` trong Cookie
- Cookie `a1` hết hạn khoảng 10 phút
- Quy tắc mã hóa cập nhật trung bình 45 ngày một lần
- Tỉ lệ thành công khi tự dựng signature dưới 12%

Với team 5 người, đây là sai phân bổ nguồn lực. Thay bằng human-in-the-loop ở mục 8.

---

## 8. Marketing inspiration (pipeline riêng)

Không nhét chung với news:

| | News | Marketing mining |
|---|---|---|
| Yêu cầu | Recall cao, realtime, dedupe chặt | Precision cao, volume nhỏ |
| Cadence | Hàng ngày | Hàng tuần hoặc 2 tuần |
| Output | Digest để đọc | Content brief để sản xuất |
| Volume | 5 đến 15 item/ngày | 20 đến 30 post/tháng |

### Luồng human-in-the-loop

```
Tùng/Vũ thấy post hay trên XHS hoặc WeChat
  → share link vào Zalo group riêng
  → bắt link qua Zalo KHub — CHƯA CHỐT cơ chế (trước đây định dùng n8n, nay bỏ; cần chọn
    lại: webapp tự poll Zalo KHub API, hay qua Pancake MCP, hay Claude connector đọc trực
    tiếp — xem ghi chú đầu mục 2)
  → screenshot + OCR (nội dung XHS chủ yếu là 图文)
  → Haiku phân tích: hook, cover style, title pattern, pain point
  → sinh brief tiếng Việt
  → ghi vào marketing.inspiration (status = 'idea')
  → digest tuần gửi Vũ
```

### Nguyên tắc nội dung

Phần lớn nội dung 全屋智能 trên XHS là tầm Tuya/Aqara, không phải KNX. Giá trị nằm ở **cách trình bày**, không phải nội dung: cách đặt vấn đề cho chủ nhà, bố cục ảnh, cấu trúc tiêu đề, cách xử lý phản đối về giá.

Lấy format, không lấy nội dung. Copy trực tiếp vừa sai bản quyền vừa không hợp thị trường VN.

WeChat 公众号 của hãng thì ngược lại: nội dung kỹ thuật chất lượng cao, dùng cho B2B blog angle trên knxstore.vn.

---

## 9. Triển khai trên OrbStack

### 9.1 Điểm phải xử lý

| # | Vấn đề | Cách xử lý |
|---|---|---|
| 1 | ~~Container cần chung network với Postgres 5433 và n8n~~ — hết áp dụng, không còn n8n trong kiến trúc (xem ghi chú đầu mục 2). Container chỉ cần chung network với Postgres 5433 | Dùng external network, không map port ra host |
| 2 | Wechat2RSS có thể chỉ có build amd64 | Khai báo `platform: linux/amd64`, chạy qua Rosetta. Workload nhẹ nên không ảnh hưởng hiệu năng |
| 3 | Playwright trên ARM64 | Tách container riêng `news-renderer`, không nhồi vào image extractor (nặng ~1.5GB, mà 75 đến 85% nguồn không cần). Cần test tag image trước khi chốt |
| 4 | Mac sleep làm miss cron | Kiểm tra `pmset -g \| grep sleep`. Cần `disablesleep 1`. OrbStack phải bật Start at login. Cân nhắc auto-login cho user `tungvu` |
| 5 | Outbound tới api.anthropic.com | Kiểm tra container ra internet được, không bị chặn bởi cấu hình proxy hiện tại |

**Không còn vấn đề networking tới Ollama và ràng buộc RAM cho model 8B**, do bỏ local. Đây là lợi ích vận hành lớn nhất của quyết định này.

### 9.2 Tài nguyên ước tính

| Container | RAM | Ghi chú |
|---|---|---|
| news-extractor | 300 đến 500 MB | trafilatura nhẹ |
| news-renderer | 600 MB đến 1 GB | Chỉ khi chạy, có thể scale to 0 |
| wechat2rss | 200 đến 400 MB | |

Tổng thêm dưới 2 GB. Không cần đánh giá lại headroom của Mac Mini.

---

## 10. Kế hoạch triển khai

### Track A: Registry Diff (ưu tiên cao nhất)

| # | Việc | Ước tính | Phụ thuộc |
|---|---|---|---|
| A1 | Schema `registry` + import CSV KNX 10,195 devices có sẵn | 3 đến 4h | |
| A2 | Viết crawler KNX mới, chạy theo lịch (build mới hoàn toàn, không tái sử dụng crawler cũ) | 4 đến 6h | A1 |
| A3 | Bảng `brands_of_interest` + logic diff | 3 đến 4h | A2 |
| A4 | Crawler CSA Matter certified DB | 5 đến 8h | A1 |
| A5 | n8n workflow weekly + gửi Zalo | 2 đến 3h | A3 |

**Tổng: 17 đến 25 giờ.** Track A cho ra giá trị trước cả khi news pipeline chạy. Nếu thiếu người, làm mỗi track này.

### Track B: News Pipeline

**Cập nhật (2026-08-14) — B0 đã làm khác kế hoạch gốc:** thay vì `sources.yaml` trong git +
loader script, `news.sources` (schema + bảng) được tạo trực tiếp bằng migration SQL
(`track-a/migrations/0004_create_news_sources.sql`, `0005_seed_news_sources.sql`) chạy trên
**Postgres dev của Track A** (registry-postgres, port 5433) — dùng chung 1 Postgres thay vì
tách riêng, và quản lý bật/tắt/thêm nguồn qua UI có sẵn (`track-a/webapp/templates/
settings.html`, mục "Nguồn crawl content — Track B") thay vì sửa file `sources.yaml` rồi
redeploy. Đã seed **35 nguồn** (không phải 40) — xem `docs/sources-content-research.md` để
biết danh sách gốc 54 URL đã test và lý do loại 19 URL (chết/chặn bot/redirect sai). 17/35
nguồn `kind=html_list` chưa có `extract_rule` (selector rỗng) — cần bổ sung trước khi B1
chạy được với nhóm này.

| Sprint | Việc | Ước tính | Definition of Done |
|---|---|---|---|
| **B0** | Schema `news` + `marketing` + migration script | 4 đến 6h | Chạy được trên Postgres 5433, có rollback |
| **B0** | ~~`sources.yaml` seed 40 nguồn + loader~~ | 6 đến 8h | 🟡 Đã làm khác kế hoạch — xem ghi chú dưới bảng |
| **B1** | Container `news-extractor` | 8 đến 12h | POST /extract trả đúng schema, fail rate < 20% trên 40 nguồn |
| **B1** | ~~n8n workflow~~ Webapp fetch (trigger tay qua UI/Claude connector, giống Track A) + ghi `fetch_log`, `source_health` | 6 đến 8h | Nguồn chết 3 lần liên tiếp gửi cảnh báo |
| **B2** | Dedupe tầng 1 (canonical URL) | 3 đến 4h | Test case: 20 URL có tracking param, gồm cả spm và WeChat param |
| **B2** | Dedupe tầng 2 (SimHash + band index) | 6 đến 8h | Cùng bài crawl 2 lần cách 1h không tạo record mới |
| **B3** | Tầng 1 triage qua Batch API + `batch_jobs` | 8 đến 10h | JSON parse rate > 95% trên 100 bài. Batch poll và retry hoạt động |
| **B3** | Luồng realtime bypass + hard rule | 4 đến 6h | Bài tier 1 + brand match ra alert trong < 1 phút |
| **B4** | Event clustering bằng Haiku | 6 đến 8h | Test trên 100 bài có nhãn thủ công, precision > 80% |
| **B4** | Tầng 2 deep analysis | 4 đến 6h | |
| **B5** | Ranking + digest render + gửi Zalo KHub / Telegram | 6 đến 8h | Digest có nút feedback |
| **B5** | Feedback loop ghi `news.feedback` | 4 đến 6h | Rating ghi được từ Zalo |
| **B6** | Wechat2RSS self-host + tài khoản phụ | 4 đến 8h | 10 公众号 ra feed |
| **B6** | `news-renderer` Playwright fallback | 6 đến 8h | Chỉ làm nếu extract fail rate > 20% ở B1 |

**Tổng Track B: 75 đến 106 giờ.** Với 1 dev part-time 50%, khoảng 5 đến 7 tuần.

Nếu cần cắt xuống 3 tuần: bỏ B4 (event clustering), B6 (WeChat + renderer). Chấp nhận digest bị trùng lặp và mất nguồn TQ chất lượng cao.

**Đề xuất rút gọn để test giả thuyết sớm:** Rủi ro lớn nhất của cả dự án là "digest bị bỏ đọc" (mục 12), nhưng theo trình tự B0→B5 phải mất 63-84h (~4-5 tuần) mới có digest đầu tiên để kiểm chứng. Thay vào đó, chạy song song với Track A một **digest thô** ngay từ tuần 1-2: chỉ cần B0 + dedupe tầng 1 (canonical URL) + triage tầng 1, bỏ qua SimHash (tầng 2) và event clustering (B4). Mục đích là có dữ liệu đọc thật (rating từ Tùng) sớm nhất, trước khi đầu tư thêm 12-16h vào B2 + B4 mà chưa biết thói quen đọc có hình thành hay không.

### Track C: Marketing (sau khi B5 xong)

| # | Việc | Ước tính |
|---|---|---|
| C1 | Schema `marketing` + workflow bắt link từ Zalo | 4 đến 6h |
| C2 | OCR + Haiku phân tích hook/format | 6 đến 8h |
| C3 | Digest tuần gửi Vũ | 3 đến 4h |

---

## 11. Tiêu chí Go / No-Go

Đo sau **14 ngày** kể từ khi digest chạy ổn định:

| Chỉ số | Ngưỡng Go | Nếu không đạt |
|---|---|---|
| Useful rate (rating ≥ 1 trên tổng item vào digest) | ≥ 40% | Vấn đề ở **nguồn và prompt**, không phải kiến trúc. Dựng thêm infra không cứu được |
| Alert precision (rating ≥ 1 trên tổng alert) | ≥ 70% | Siết hard rule, giảm brand list |
| Extract fail rate | ≤ 20% | Làm B6 renderer |
| Event clustering precision | ≥ 80% | Sửa prompt, siết ràng buộc gom nhóm |
| Số nguồn chết (consecutive_failures ≥ 3) | ≤ 15% tổng nguồn | Rà lại selector |
| Chi phí API thực tế | ≤ $15/tháng | Bật prompt caching, siết truncate input |
| Thời gian Tùng đọc digest | ≥ 5 ngày/tuần | Nếu không đọc thì dừng dự án, không phải sửa hệ thống |

Chỉ mở scope ở mục 1.2 khi cả 7 chỉ số đạt.

---

## 12. Rủi ro

| Rủi ro | Xác suất | Tác động | Giảm thiểu |
|---|---|---|---|
| Digest bị bỏ đọc sau 2 tuần | **Cao** | **Cao** | Rủi ro lớn nhất của dự án. Giới hạn cứng 5 item/ngày. Feedback loop từ ngày đầu |
| Nguồn RSS chết âm thầm | Cao | Cao | `source_health` là bắt buộc, không phải nice-to-have |
| Extract fail cao trên site TQ | Cao | Trung bình | Dự trù B6 renderer ngay từ đầu, đừng để phát hiện muộn |
| Event clustering gom quá rộng | Trung bình | Trung bình | Ràng buộc prompt phải gom theo sự kiện cụ thể, không theo chủ đề. Test có nhãn trước |
| Batch API trả kết quả chậm hơn dự kiến | Trung bình | Thấp | Luồng alert đã tách sang realtime. Digest trễ 1 ngày chấp nhận được |
| Tài khoản WeChat bị hạn chế | Trung bình | Thấp | Tài khoản phụ, không dùng tài khoản cá nhân |
| Rate limit Claude API khi backfill | Trung bình | Thấp | Backfill lịch sử qua Batch API, không qua Messages API |
| Mac Mini là single point of failure | Thấp | Cao | Backup schema hàng ngày. Chấp nhận downtime ở giai đoạn này |
| Pipeline tự fail (container crash, mất kết nối DB, batch job kẹt) không được phát hiện — `source_health` chỉ theo dõi nguồn, không theo dõi chính pipeline | Trung bình | Cao | Thêm healthcheck riêng: nếu không có digest gửi đúng giờ đã định → alert qua kênh độc lập, không phụ thuộc vào chính n8n workflow đang lỗi |
| Giá API thay đổi | Thấp | Thấp | Ở mức $5/tháng, kể cả tăng 3x vẫn không ảnh hưởng quyết định |

---

## 13. Phân công

| Người | Trách nhiệm |
|---|---|
| Tùng | Duyệt `sources.yaml`, định nghĩa `brands_of_interest` (gồm alias tiếng Trung), chấm feedback 100 item đầu, quyết Go/No-Go |
| Dev nội bộ | Track A và B toàn bộ |
| Vũ | Track C, cung cấp input marketing angle |

**Việc Tùng không được delegate:** chấm feedback 100 item đầu và gán nhãn 100 bài cho test event clustering. Không có 2 tập dữ liệu này thì prompt không tinh chỉnh được và hệ thống sẽ dừng ở mức nhiễu.

**Chưa chốt:** "Dev nội bộ" hiện chưa map vào người cụ thể trong 5 nhân sự (Tùng/Thảo/Vũ/Huy). Nếu Vũ đảm nhận, cần cân đối với Track C và trách nhiệm Sales B2C + Dev Web hiện tại — ước tính 92-131h (Track A+B) là không thực tế nếu chỉ làm ngoài giờ rảnh. Cần chốt người trước khi commit timeline ở mục 10.

---

## 14. Quyết định cần chốt trước khi code

| # | Quyết định | Ảnh hưởng |
|---|---|---|
| 1 | `brands_of_interest` lấy tự động từ KNX Master Data MCP hay khai báo tay? Cần alias tiếng Trung cho nguồn CN | Hard rule §6.2, ranking §6.4 |
| 2 | Telegram bot mới hay dùng lại bot trong hệ Hermes đang dựng dở? | B5 |
| 3 | Có chấp nhận rủi ro tài khoản WeChat phụ không? Nếu không thì bỏ 15 nguồn 公众号 | Giảm ~30% coverage nguồn TQ |
| 4 | Digest gửi riêng Tùng hay cả team? Nếu cả team thì kênh Zalo nào? | B5 |
| 5 | Ngân sách Claude API trần hàng tháng để set alert | §11 |
| 6 | Có làm Track A trước hay chạy song song A và B? | Phụ thuộc số dev khả dụng |

---

## Phụ lục: thay đổi từ v1.0

| Mục | v1.0 | v1.1 |
|---|---|---|
| Tầng 1 triage | qwen3:8b local | Haiku 4.5 qua Batch API |
| Embedding | bge-m3 local, 1024 dim | Bỏ hoàn toàn |
| Event clustering | Vector cosine ≥ 0.85 | LLM, 1 call/ngày |
| Dedupe | 3 tầng | 2 tầng (URL + SimHash) |
| Chi phí | ~$2/tháng (chỉ tầng 2) | ~$5/tháng |
| Container mới | 2 | 2 (+1 tùy chọn) |
| Rủi ro model 8B với tiếng Trung | Có | Loại bỏ |
| Ràng buộc RAM Mac Mini | Có, cần đánh giá | Không đáng kể |
| Ước tính Track B | 67 đến 96h | 75 đến 106h |
| Orchestrator (2026-08-14) | n8n (`n8n.tungvu.vn`) | Bỏ n8n — trigger tay qua UI webapp hoặc Claude/MCP connector, giống Track A |
