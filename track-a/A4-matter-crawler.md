# A4 — Crawler CSA Matter certified DB

Ước tính gốc: 5-8h · **Đã research xong, thực tế dễ hơn nhiều so với dự đoán** (xem dưới) ·
Phụ thuộc: A1 · Xem [00-overview.md](00-overview.md).

## Mục tiêu

Tương tự A2 nhưng cho CSA Matter certified product database, ghi vào cùng
`registry.devices`/`registry.snapshots` với `registry_key = 'matter_csa'`. Toàn bộ logic
UPSERT, anomaly check, crawl_log dùng lại y hệt A2 — khác biệt duy nhất là nguồn dữ liệu.

## Nguồn dữ liệu — đã research + test thật (không phải HTML scrape như KNX)

CSA Matter không cần scrape HTML. Chứng nhận Matter được công bố công khai trên
**Distributed Compliance Ledger (DCL)** — sổ cái blockchain permissioned của CSA, có REST API
đọc công khai (permissionless cho read), do CSA Alliance vận hành observer node.

**Endpoint đã test thật, trả JSON:**

```
https://on.dcl.csa-iot.org/dcl/model/models?pagination.limit=1000
https://on.dcl.csa-iot.org/dcl/vendorinfo/vendors?pagination.limit=1000
```

Kết quả test:
- Tổng **4.948 model**, **459 vendor** (nhỏ hơn nhiều so với 10.167 devices của KNX).
- `pagination.limit=1000` hoạt động → toàn bộ model chỉ cần **~5 request** (không phải 848
  trang như KNX), vendor chỉ cần **~1 request**.
- Pagination kiểu Cosmos SDK chuẩn: response có `pagination.next_key` — dùng
  `pagination.key=<next_key>` cho request tiếp theo, dừng khi `next_key` rỗng.
- Không có anti-bot, không có rate-limit thấy được khi test — đây là API chính thức, không
  phải site cần né chặn như lo ngại ban đầu.

### Cấu trúc dữ liệu thật

`/dcl/model/models` trả về mảng `model[]`, mỗi phần tử có (rút gọn, field đầy đủ dài hơn):
```json
{
  "vid": 1,
  "pid": 257,
  "deviceTypeId": 114,
  "productName": "CS/CU-HU18ZKY",
  "productLabel": "CS/CU-HU18ZKY",
  "partNumber": "-"
}
```

`/dcl/vendorinfo/vendors` trả về mảng `vendorInfo[]`:
```json
{
  "vendorID": 1,
  "vendorName": "Panasonic",
  "companyLegalName": "Panasonic Holdings Corporation",
  "vendorLandingPageURL": "https://holdings.panasonic/global/"
}
```

**Brand nằm ở bảng vendor riêng, join qua `vid` (model) = `vendorID` (vendor)** — khác KNX
(brand nằm ngay trong card thiết bị).

**`deviceTypeId`** là mã số theo chuẩn Matter (ví dụ `114`) — muốn ra tên dễ đọc (On/Off
Light, Door Lock...) cần bảng tra cứu riêng theo Matter spec. **Không làm ở v1** — để nguyên
số trong `attributes`, tương tự quyết định bỏ category/device_type ở A2 cho KNX.

### Field mapping v1

| Cột `registry.devices` | Lấy từ đâu |
|---|---|
| `external_id` | `vid` + `pid` ghép lại, ví dụ `"1-257"` — cặp này là khoá thật của model trên DCL |
| `brand` | Join `vid` → `vendorInfo.vendorName` |
| `model` | `productName` (hoặc `productLabel` nếu khác) |
| `category` / `device_type` | Không map ở v1 — giữ `deviceTypeId` thô trong `attributes` |
| `cert_date` | Chưa kiểm tra — DCL có thể có field thời gian ở transaction/block, cần xem thêm nếu cần (không chặn v1) |
| `attributes` | `{deviceTypeId, partNumber, vendorLandingPageURL}` |

## Không cần Playwright, không cần container riêng

Vì là REST API JSON thuần, không cần `news-renderer`/Playwright — bỏ hẳn phần lo ngại anti-bot
ở bản trước. Có thể dùng chung 1 image Docker với crawler KNX (A2) — cùng là script Python gọi
HTTP, khác nguồn. Không cần quyết định "dùng chung hay tách container" nữa.

## Ước tính lại

5-8h ban đầu dựa trên giả định phải scrape HTML + xử lý anti-bot — không còn đúng. Việc còn
lại chỉ là: viết script gọi API JSON (đơn giản hơn parse HTML nhiều), join vendor vào model,
UPSERT như A2. Thực tế nhiều khả năng dưới 3h, nhưng để dev tự chốt lại sau khi bắt tay code.

## Hành vi (giống A2, khác nguồn)

```
Fetch toàn bộ /dcl/vendorinfo/vendors (build map vendorID -> vendorName)
  │
  ▼
Fetch toàn bộ /dcl/model/models (phân trang bằng next_key)
  │
  ▼
Join brand = vendorMap[vid], external_id = f"{vid}-{pid}"
  │
  ▼
Cùng flow UPSERT / anomaly check / crawl_log như A2, registry_key = 'matter_csa'
```

## Definition of Done

- [x] Research: xác nhận có API JSON công khai, không cần scrape HTML/Playwright
- [x] Xác nhận tổng số lượng thật (4.948 model, 459 vendor) qua test trực tiếp
- [ ] Crawler chạy 1 lần, ghi đúng số lượng sản phẩm vào `registry.snapshots`
      (registry_key = 'matter_csa')
- [ ] Join vendor đúng — spot-check vài `vid` xem tên hãng ra đúng không
- [ ] Cùng bộ test case anomaly/duplicate như A2, áp dụng cho `matter_csa`
