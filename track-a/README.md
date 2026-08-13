# Track A — Registry Diff: Kế hoạch build

Tách từ [`../docs/plan.md`](../docs/plan.md) §2.3, §4.3, §10 (Track A). Track A độc lập hoàn
toàn với News Pipeline (Track B), ưu tiên cao nhất, không dùng LLM. Mục tiêu: phát hiện thiết
bị mới trong các registry chứng nhận (KNX, CSA Matter, DALI) sớm hơn press release 2-8 tuần.

Tổng ước tính gốc: 17-25h (§10). Thực tế: phần lớn A1-A4 đã code + test xong (xem mục 0), thấp
hơn ước tính ban đầu nhờ CSA Matter có API JSON (không cần scrape).

---

## 0. Trạng thái hiện tại

| # | Việc | Trạng thái |
|---|---|---|
| A1 | Schema `registry` + migration | ✅ Chạy thật trên Postgres dev cục bộ (`src/docker-compose.yml`), không còn chỉ là test |
| A2 | Crawler KNX + UPSERT/diff | ✅ Code + test xong. Baseline thật đã crawl **và import vào Postgres dev** — 10.167 thiết bị đang nằm trong `registry.devices` |
| A3 | `brands_of_interest` + diff logic | ✅ 73 brand thật đã seed vào Postgres dev, 12 brand có alias verify bằng dữ liệu crawl thật. Query match thật cho ra 34 nhóm brand/registry khớp. Vài entry chờ Tùng xác nhận thêm |
| A4 | Crawler CSA Matter | ✅ Code + test xong. Baseline thật đã crawl **và import vào Postgres dev** — 4.948 thiết bị đang nằm trong `registry.devices` |
| A5 | n8n workflow + Zalo | 🟡 Đang làm — query diff + format message xong trong n8n-dev, **thiếu node gửi Zalo thật** + check crawl fail/anomaly. Xem "Việc chưa giải quyết" trong [A5-n8n-workflow.md](A5-n8n-workflow.md) |

**Cập nhật (2026-08-13): đã dựng Postgres dev cục bộ chạy thật** (không phải container tạm
xoá sau test) — `track-a/src/docker-compose.yml`, image `pgvector/pgvector:pg17` khớp
`docs/plan.md` §2.1. Đã apply migration 0001+0002, import baseline KNX (10.167) + Matter
(4.948) thật vào — không còn là "chỉ test", đây là dữ liệu sống, persistent qua Docker volume.

Query match brand thật cho kết quả: **34 nhóm brand/registry khớp**, tổng hàng nghìn thiết bị
(MDT technologies: 1.037, ABB 3 chi nhánh: 1.365, Elsner: 266, Aqara: 118...). Đây là dữ liệu
thật sẽ vào digest khi A5 xong.

Credential nằm trong `track-a/src/.env` (không commit — xem `.env.example` để biết cấu trúc).
**Đây là Postgres dev, chạy trên máy đang code — chưa phải Postgres 5433 thật trên Mac Mini.**
Khi chuyển lên Mac Mini, chỉ cần export lại data + trỏ `.env` sang host mới, schema/code không
đổi gì.

**Việc còn chặn thật sự (2026-08-13):** node gửi Zalo KHub thật trong A5 — n8n-dev không có
credential KHub (chỉ có ở n8n production `n8n.tungvu.vn`, xem chi tiết trong
[A5-n8n-workflow.md](A5-n8n-workflow.md) mục "Việc chưa giải quyết"). Ngoài ra `launchd` chạy
crawler tự động đang bị macOS TCC chặn, cần tự cấp Full Disk Access cho `/bin/bash` — chạy tay
vẫn hoạt động bình thường. Postgres không còn chặn gì ở mức dev/test nữa.

---

## 1. Cấu trúc thư mục

```
track-a/
├── README.md                  ← file này
├── A1-schema-import.md        Schema + import baseline
├── A2-knx-crawler.md          Crawler KNX + logic UPSERT/diff (dùng chung cho A4)
├── A3-brands-diff.md          brands_of_interest + query match brand
├── A4-matter-crawler.md       Crawler CSA Matter (DCL API)
├── A5-n8n-workflow.md         n8n workflow + gửi Zalo
├── migrations/
│   ├── 0001_create_registry_schema.sql
│   ├── 0001_create_registry_schema.down.sql
│   └── 0002_seed_brands_of_interest.sql
├── src/                       Toàn bộ code — Python + Docker
│   ├── crawl_knx_devices.py
│   ├── crawl_matter_devices.py
│   ├── import_and_diff.py     UPSERT + anomaly check + crawl_log (dùng chung KNX/Matter)
│   ├── requirements.txt
│   ├── Dockerfile                     đóng gói crawler
│   ├── docker-compose.snippet.yml     snippet để dev ghép vào compose thật của n8n stack
│   ├── docker-compose.yml             Postgres DEV chạy thật (không commit .env)
│   └── .env.example                   mẫu credential — copy thành .env, điền thật
└── data/                      CSV baseline thật đã crawl + reference data KNXStore
    ├── knx_devices_baseline.csv       (10.167 dòng)
    ├── matter_devices_baseline.csv    (4.948 dòng)
    ├── knxstore-brands-raw.txt        (75 brand KNXStore cung cấp)
    └── knxstore-categories.csv        (90 category KNXStore)
```

## 2. Trình tự build và phụ thuộc

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
| [A4-matter-crawler.md](A4-matter-crawler.md) | Crawler CSA Matter certified DB | 5-8h → thực tế thấp hơn (xem file) |
| [A5-n8n-workflow.md](A5-n8n-workflow.md) | n8n workflow weekly + gửi Zalo | 2-3h |

---

## 3. Deviation so với kế hoạch gốc — cần biết trước khi build

**`brands_of_interest` chuyển từ schema `news` sang schema `registry`.**

Kế hoạch gốc (`../docs/plan.md` §4.1) định nghĩa `news.brands_of_interest`, nhưng bảng này
lại được dùng ở Track A (§10, dòng A3) — trong khi Track A được thiết kế "độc lập với news
pipeline" (§2.3). Nếu giữ nguyên trong schema `news`, Track A sẽ phụ thuộc ngược vào Track B
chưa tồn tại.

→ Quyết định trong bộ file này: tạo `registry.brands_of_interest` làm nguồn duy nhất, build
ngay ở A3. Khi build Track B sau này, `news` schema tham chiếu thẳng bảng này thay vì định
nghĩa lại — tránh trùng lặp dữ liệu brand giữa 2 schema.

**Đã đồng bộ vào `../docs/plan.md`** (§4.1, §4.3, §10) — `brands_of_interest` và `crawl_log`
giờ nằm trong schema `registry`, file đó là nguồn chuẩn.

**Thêm bảng `registry.crawl_log`** (không có trong schema gốc §4.3) — lý do: không có cách nào
theo dõi lịch sử chạy crawler (KNX, CSA Matter) nếu không có bảng log riêng, tương tự vai trò
`news.fetch_log` bên Track B. Không có bảng này thì crawl fail âm thầm sẽ không ai biết —
đúng loại rủi ro đã ghi trong kế hoạch chính §12 ("nguồn chết âm thầm"), áp dụng y hệt cho
Track A. Chi tiết ở [A2-knx-crawler.md](A2-knx-crawler.md).

---

## 4. Đã chốt

- **A2 build crawler KNX mới hoàn toàn, không tái sử dụng/refactor code cũ.** CSV 10.195
  devices ở A1 chỉ dùng làm baseline import, không liên quan đến việc viết crawler mới.
- **CSA Matter dùng DCL API JSON**, không scrape HTML — xem [A4-matter-crawler.md](A4-matter-crawler.md).
- **Bug lệch đồng hồ script/Postgres đã tìm và sửa** trong `import_and_diff.py` — xem
  [A2-knx-crawler.md](A2-knx-crawler.md) mục "Đã viết và test thật".

**Phát hiện mới: `docs/plan.md` §2.3 nhắc "DALI Alliance product DB" là 1 trong 3 registry của
Track A, nhưng bảng task §10 chưa từng có task crawl DALI nào (chỉ A2=KNX, A4=Matter).** Lộ ra
khi đối chiếu brand list thật của KNXStore với dữ liệu đã crawl: 30/75 brand không tìm thấy,
phần lớn thuộc hệ sinh thái Casambi/DALI (Casambi, Trivum, Philips Hue, Carus, IR-TEC...) —
đúng như dự đoán nếu chưa crawl nguồn đó. Chưa thêm task DALI vào Track A ở đây — để Tùng
quyết định có cần không trước khi mở rộng scope.

## 5. Việc cần xác nhận trước khi code (chưa có câu trả lời trong plan gốc)

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | CSV 10.195 devices KNX hiện đang ở đâu? *(không còn bắt buộc — đã có baseline crawl thật ở `data/knx_devices_baseline.csv`)* | A1 |
| ~~2~~ | ~~URL/API nguồn KNX certified database~~ — **Đã trả lời:** `knx.org/devices`, chi tiết ở [A2-knx-crawler.md](A2-knx-crawler.md) | A2 |
| ~~3~~ | ~~URL/cấu trúc CSA Matter DB~~ — **Đã trả lời:** API JSON công khai (DCL), không phải scrape HTML, không anti-bot. Chi tiết ở [A4-matter-crawler.md](A4-matter-crawler.md) | A4 |
| 4 | Danh sách `brands_of_interest` ban đầu | **Đã nhận, chốt 75 brand** (không phải 80 như nhãn ban đầu) + 90 category, xem `data/knxstore-brands-raw.txt`, `data/knxstore-categories.csv`. Seed SQL đã viết + test: [`migrations/0002_seed_brands_of_interest.sql`](migrations/0002_seed_brands_of_interest.sql). `Kanonbus` đã xác nhận là brand thật. Còn `RESI`, `Systemline E50`, `OEM`, `Maximum Security` chưa xác nhận — không chặn gì, chỉ chưa có alias. Alias tiếng Trung: chưa cần (danh sách hiện tại chưa có brand CN rõ ràng) |
| ~~5~~ | ~~Thông tin kết nối Postgres 5433 thật~~ — **tạm thời không cần:** đã dựng Postgres dev cục bộ (`src/docker-compose.yml`), đủ để chạy toàn bộ Track A. Khi có Postgres 5433 thật trên Mac Mini, chỉ cần export data + đổi `.env`, không phải làm lại gì | A1 |
| ~~6~~ | ~~Ngưỡng "removed" khi crawl trả về ít device hơn lần trước~~ — **Đã code + test:** mặc định 0.8 (abort nếu giảm hơn 20% so với avg lịch sử), tham số `--anomaly-threshold` chỉnh được, xem [A2-knx-crawler.md](A2-knx-crawler.md) | A2 |

Chỉ còn mục 4 và 5 thật sự chặn đường — cả hai đều là quyết định/thông tin của Tùng, không
phải việc kỹ thuật.
