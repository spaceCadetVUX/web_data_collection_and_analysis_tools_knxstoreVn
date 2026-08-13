# Track A — Registry Diff: Kế hoạch build

Tách từ `knx-news-agent-plan.md` §2.3, §4.3, §10 (Track A). Track A độc lập hoàn toàn với
News Pipeline (Track B), ưu tiên cao nhất, không dùng LLM. Mục tiêu: phát hiện thiết bị mới
trong các registry chứng nhận (KNX, CSA Matter, DALI) sớm hơn press release 2-8 tuần.

Tổng ước tính: **17-25h**, đúng như §10 gốc.

---

## 1. Trình tự build và phụ thuộc

```
A1 (schema + import CSV KNX)
  │
  ├──► A2 (crawler KNX theo lịch) ──► A3 (brands_of_interest + diff)
  │                                        │
  └──► A4 (crawler CSA Matter, song song A2)   │
                                               ▼
                                        A5 (n8n weekly + gửi Zalo)
```

A2 và A4 có thể làm song song sau khi A1 xong (cả hai chỉ phụ thuộc schema, không phụ thuộc
lẫn nhau). A3 cần A2 chạy được ít nhất 1 lần để có dữ liệu test diff. A5 cần A3 xong.

| File | Việc | Ước tính |
|---|---|---|
| [A1-schema-import.md](A1-schema-import.md) | Schema `registry` + import CSV KNX 10.195 devices | 3-4h |
| [A2-knx-crawler.md](A2-knx-crawler.md) | Viết crawler KNX mới, chạy theo lịch | 4-6h |
| [A3-brands-diff.md](A3-brands-diff.md) | `brands_of_interest` + logic diff | 3-4h |
| [A4-matter-crawler.md](A4-matter-crawler.md) | Crawler CSA Matter certified DB | 5-8h |
| [A5-n8n-workflow.md](A5-n8n-workflow.md) | n8n workflow weekly + gửi Zalo | 2-3h |

---

## 2. Deviation so với kế hoạch gốc — cần biết trước khi build

**`brands_of_interest` chuyển từ schema `news` sang schema `registry`.**

Kế hoạch gốc (`knx-news-agent-plan.md` §4.1) định nghĩa `news.brands_of_interest`, nhưng
bảng này lại được dùng ở Track A (§10, dòng A3) — trong khi Track A được thiết kế "độc lập
với news pipeline" (§2.3). Nếu giữ nguyên trong schema `news`, Track A sẽ phụ thuộc ngược vào
Track B chưa tồn tại.

→ Quyết định trong bộ file này: tạo `registry.brands_of_interest` làm nguồn duy nhất, build
ngay ở A3. Khi build Track B sau này, `news` schema tham chiếu thẳng bảng này thay vì định
nghĩa lại — tránh trùng lặp dữ liệu brand giữa 2 schema.

**Đã đồng bộ vào `knx-news-agent-plan.md`** (§4.1, §4.3, §10) — `brands_of_interest` và
`crawl_log` giờ nằm trong schema `registry`, file chính là nguồn chuẩn.

**Thêm bảng `registry.crawl_log`** (không có trong schema gốc §4.3) — lý do: không có cách nào
theo dõi lịch sử chạy crawler (KNX, CSA Matter) nếu không có bảng log riêng, tương tự vai trò
`news.fetch_log` bên Track B. Không có bảng này thì crawl fail âm thầm sẽ không ai biết —
đúng loại rủi ro đã ghi trong kế hoạch chính §12 ("nguồn chết âm thầm"), áp dụng y hệt cho
Track A. Chi tiết ở A2-knx-crawler.md.

---

## 3. Đã chốt

- **A2 build crawler KNX mới hoàn toàn, không tái sử dụng/refactor code cũ.** CSV 10.195
  devices ở A1 chỉ dùng làm baseline import, không liên quan đến việc viết crawler mới.

## 4. Việc cần xác nhận trước khi code (chưa có câu trả lời trong plan gốc)

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | CSV 10.195 devices KNX hiện đang ở đâu? *(không còn bắt buộc — xem ghi chú dưới)* | A1 |
| ~~2~~ | ~~URL/API nguồn KNX certified database~~ — **Đã trả lời:** `knx.org/devices`, chi tiết ở [A2-knx-crawler.md](A2-knx-crawler.md) | A2 |
| 3 | URL/cấu trúc chính xác của CSA Matter certified DB — có phân trang, có anti-bot (Cloudflare) không? | A4 — ước tính 5-8h có thể lệch nhiều nếu cần xử lý anti-bot |
| 4 | Danh sách `brands_of_interest` ban đầu — Tùng cung cấp lúc nào? Alias tiếng Trung cần cho brand nào? | A3 |
| 5 | Thông tin kết nối Postgres 5433 (host, credential) để chạy migration | A1 |
| 6 | Ngưỡng "removed" khi crawl trả về ít device hơn lần trước — coi là thật hay coi là crawl lỗi? | A2 — quyết định sai có thể đánh dấu nhầm hàng loạt device đang active thành removed |

**Câu 1 hạ mức ưu tiên:** đã tìm ra crawler A2 có thể tự tạo baseline trực tiếp từ
`knx.org/devices` (xem A2-knx-crawler.md), không bắt buộc phải có CSV cũ nữa. Nếu CSV có sẵn
thì dùng để tiết kiệm thời gian crawl baseline lần đầu; nếu không có thì bỏ qua bước import,
chạy thẳng crawler.

Mục 3, 4, 5 vẫn cần input từ Tùng trước khi bắt tay vào code — không đoán được từ trong plan.
