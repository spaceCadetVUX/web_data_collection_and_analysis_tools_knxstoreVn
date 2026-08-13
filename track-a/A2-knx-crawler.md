# A2 — Crawler KNX chạy theo lịch

Ước tính: 4-6h · Phụ thuộc: A1 · Xem [00-overview.md](00-overview.md) cho bối cảnh.

## Mục tiêu

Build crawler KNX **mới hoàn toàn** (đã xác nhận: không tái sử dụng/refactor crawler đã dùng
để tạo CSV 10.195 devices ở A1 — CSV đó chỉ dùng làm baseline import, không dùng lại code).
Script chạy theo lịch (weekly), tự động diff với dữ liệu đã lưu, cập nhật `registry.devices`
và `registry.snapshots`.

## Nguồn dữ liệu (đã research + verify trực tiếp trên HTML thô, câu hỏi #2 ở overview đã trả lời)

**https://www.knx.org/devices** — site KNX Association đã đổi cấu trúc (Drupal), URL cũ trong
kế hoạch gốc không còn dùng được. Không có JSON API công khai (`/jsonapi` → 404) — bắt buộc
scrape HTML.

- Phân trang: `?page=0` đến `?page=847`, 12 thiết bị/trang (đã đếm chính xác từ HTML thô),
  tổng **10.167 kết quả** hiện tại (khớp gần đúng với "10.195" trong kế hoạch gốc — xác nhận
  đúng nguồn).
- `robots.txt` không chặn `/devices`, không có `Crawl-delay` khai báo → tự giới hạn ~1
  req/giây, không dựa vào site tự quy định.
- **Trang danh sách** (`/devices?page=N`) có: ảnh, tên model (`h4`), tên hãng (`span`), link
  chi tiết (`a.node-device-card__wrapper` → `/devices/{slug}`). CSS selector đã verify trực
  tiếp trên HTML thô (không đoán), dùng trong script bên dưới.
- **Trang chi tiết** (`/devices/{slug}`) — bảng `project-details-table` có: Catalog Item Name,
  Application Program Name, Order Number, Rail Mounted, Manufacturer Website, + link
  datasheet PDF.

**Đính chính so với bản trước:** `Category` và `Device Type` **không tồn tại** trên trang chi
tiết (bản trước ghi có — đó là do model tóm tắt suy diễn sai, đã verify lại bằng HTML thô và
xác nhận không có). 2 field này chỉ tồn tại dưới dạng **filter ở trang danh sách**
(`field_device_category_value[lighting]=lighting` → test thật trả về 65/10.167 kết quả, xác
nhận filter hoạt động), muốn biết category của 1 device cụ thể phải dò ngược qua toàn bộ filter
— tốn kém, chưa rõ chi phí thật, **không làm ở v1**.

**`cert_date` không có nguồn ở bất kỳ đâu** (danh sách lẫn chi tiết) — cột này sẽ luôn `NULL`
cho `registry_key = 'knx'`.

### Field mapping v1 — chỉ cần trang danh sách, KHÔNG cần vào trang chi tiết

Mục đích cốt lõi của Track A là biết "hãng X vừa có model Y mới" — thông tin này có đủ ngay ở
trang danh sách, không cần crawl 10.167 trang chi tiết:

| Cột `registry.devices` | Lấy từ đâu | Nguồn |
|---|---|---|
| `external_id` | Slug trong URL (`allinbox-1612-v3`) | Trang danh sách |
| `brand` | Tên hãng trong card | Trang danh sách |
| `model` | Tên model trong card | Trang danh sách |
| `category` | — | Không lấy ở v1 (xem đính chính trên) |
| `device_type` | — | Không lấy ở v1 |
| `cert_date` | — | Không có nguồn, luôn NULL |
| `attributes` | `{source_url, crawled_at}` | Trang danh sách |

Nếu sau này cần category/device_type/order_number thật sự (ví dụ Tùng muốn digest chi tiết
hơn), bổ sung bước crawl trang chi tiết **chỉ cho device mới phát hiện mỗi tuần** (số lượng
nhỏ), không crawl lại toàn bộ 10.167 thiết bị.

### Script crawl trang danh sách — đã viết và test

[`scripts/crawl_knx_devices.py`](scripts/crawl_knx_devices.py) — Python, dùng `requests` +
`beautifulsoup4` (`pip install -r scripts/requirements.txt`).

Đã test thật trên 3 trang (36 thiết bị): không có field rỗng, không có `external_id` trùng,
CSV ghi đúng định dạng.

```bash
# Test nhỏ trước (khuyến nghị chạy trước khi full)
python3 scripts/crawl_knx_devices.py --max-pages 3 --output test_run.csv

# Chạy full 848 trang (~15-20 phút ở delay mặc định 1s)
python3 scripts/crawl_knx_devices.py --output knx_devices_baseline.csv

# Resume nếu bị đứt giữa chừng (ví dụ dừng ở trang 400)
python3 scripts/crawl_knx_devices.py --start-page 400 --output knx_devices_baseline.csv --append
```

Script ghi CSV dần theo từng trang (flush ngay sau mỗi trang) — nếu bị đứt giữa chừng (mất
mạng, site chặn), dữ liệu đã crawl không mất, chỉ cần `--start-page` để tiếp tục. Output CSV
này chính là input cho bước import ở [A1-schema-import.md](A1-schema-import.md), hoặc có thể
sửa script để ghi thẳng vào Postgres cho crawl weekly sau này (xem A1 về lý do dùng CSV cho
baseline, ghi thẳng DB cho weekly).

## Hành vi mong muốn

```
Chạy 1 lần (theo cron weekly ở A5)
  │
  ▼
Fetch toàn bộ danh sách hiện tại từ KNX certified database
  │
  ▼
Ghi 1 row vào registry.snapshots (registry_key='knx', item_count=N, raw=...)
  │
  ▼
Với mỗi device fetch được:
  UPSERT vào registry.devices ON CONFLICT (registry_key, external_id) DO UPDATE
    SET last_seen_at = now(), attributes = <mới>, status = 'active'
  (device chưa từng thấy → first_seen_at mặc định now() → đây là "device mới")
  │
  ▼
Device có trong DB nhưng KHÔNG có trong lần fetch này:
  → status = 'removed' (CHỈ khi vượt qua kiểm tra anomaly — xem dưới)
  │
  ▼
Ghi kết quả vào registry.crawl_log
```

## Kiểm tra anomaly (bắt buộc — trả lời câu hỏi #6 ở overview)

Nếu item_count lần này chênh lệch quá lớn so với `avg` các lần trước (ví dụ giảm >20%),
**không tự động đánh dấu removed hàng loạt** — đây gần như chắc chắn là crawl lỗi (site đổi
cấu trúc, bị chặn, timeout giữa chừng) chứ không phải 20% device bị rút chứng nhận thật.

```
status = 'aborted_anomaly' trong crawl_log, không update registry.devices,
gửi cảnh báo riêng (không phải digest thiết bị mới, mà là cảnh báo vận hành)
```

Ngưỡng cụ thể (%) cần thống nhất với Tùng — không đoán, vì phụ thuộc vào biến động thực tế
của KNX certified DB mà hiện chưa có dữ liệu lịch sử để tính.

## Output cần cho A3

Sau mỗi lần chạy thành công, A3 cần truy vấn được: "những device nào vừa có
`first_seen_at` = lần chạy này" — dùng trực tiếp cột có sẵn, không cần thêm bảng riêng:

```sql
SELECT * FROM registry.devices
WHERE registry_key = 'knx' AND first_seen_at >= <thời điểm bắt đầu crawl lần này>;
```

## Definition of Done

- [ ] Script chạy thủ công 1 lần, ghi đúng 1 row vào `registry.snapshots`
- [ ] Device mới (giả lập bằng cách xóa 1 row rồi chạy lại) → xuất hiện lại với
      `first_seen_at` = thời điểm chạy lại, không phải thời điểm gốc
- [ ] Device bị gỡ khỏi site thật (không giả lập được dễ — test bằng cách tạm sửa 1
      `external_id` trong DB thành giá trị không tồn tại, chạy lại, kiểm tra nó
      chuyển `status = 'removed'`)
- [ ] Giả lập crawl trả về 0 hoặc rất ít kết quả (mock response rỗng) → không mass-update
      status, `crawl_log.status = 'aborted_anomaly'`
- [ ] Chạy lại script 2 lần liên tiếp với cùng dữ liệu → không tạo duplicate, không đổi
      `first_seen_at` của device cũ
