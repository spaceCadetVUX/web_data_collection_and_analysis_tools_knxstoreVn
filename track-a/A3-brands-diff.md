# A3 — `brands_of_interest` + logic diff

Ước tính: 3-4h · Phụ thuộc: A2 (cần dữ liệu thật để test diff) · Xem [00-overview.md](00-overview.md).

## Mục tiêu

Từ danh sách device mới mà A2 phát hiện (`first_seen_at` = lần crawl gần nhất), lọc ra
những device thuộc hãng nằm trong `brands_of_interest` — đây là danh sách sẽ đi vào digest/
alert ở A5. Thiết bị mới của hãng không quan tâm thì **không** báo, tránh nhiễu.

## Bảng (đã tạo ở A1, nhắc lại)

```sql
CREATE TABLE registry.brands_of_interest (
  id         serial PRIMARY KEY,
  brand      text UNIQUE NOT NULL,
  aliases    text[],
  aliases_zh text[],
  priority   smallint DEFAULT 2,
  is_active  boolean DEFAULT true
);
```

**Seed data chưa có — cần Tùng cung cấp trước khi test được logic diff thật** (câu hỏi #4
ở overview). Không tự đoán danh sách hãng, vì đây là quyết định kinh doanh (hãng nào KNXStore
đang phân phối/quan tâm), không phải quyết định kỹ thuật.

Ví dụ cấu trúc để Tùng điền (không phải seed thật):

```sql
INSERT INTO registry.brands_of_interest (brand, aliases, aliases_zh, priority) VALUES
  ('ABB', ARRAY['ABB i-bus', 'Busch-Jaeger'], NULL, 1),
  ('JUNG', ARRAY['Jung'], NULL, 1),
  ('GVS', ARRAY['GVS Smart Home'], ARRAY['视声'], 2);
```

## Vấn đề matching brand — không match exact string

`registry.devices.brand` lấy trực tiếp từ dữ liệu crawl, có thể không khớp chính xác chuỗi
trong `brands_of_interest.brand` (ví dụ crawl trả về "ABB i-bus KNX" nhưng bảng ghi "ABB").
Match phải qua cả `brand` lẫn `aliases`, không phân biệt hoa thường.

**Đã test thật bằng Postgres tạm + dữ liệu CSA Matter (4.948 thiết bị) + 2 thiết bị giả lập
mới ("TestBrand" và "ABB Test Sensor").** Query dưới đây đã xác nhận: bắt đúng thiết bị ABB
mới, loại đúng TestBrand (không trong danh sách quan tâm), **không lẫn thiết bị cũ**:

```sql
SELECT d.external_id, d.brand, d.model
FROM registry.devices d
JOIN registry.brands_of_interest b
  ON b.is_active
 AND (
      lower(d.brand) = lower(b.brand)
      OR lower(d.brand) = ANY (SELECT lower(a) FROM unnest(b.aliases) a)
     )
WHERE d.registry_key = 'knx'
  AND d.status = 'active'  -- bắt buộc: loại device vừa bị đánh removed cùng lúc
  AND d.first_seen_at >= (
    SELECT run_at FROM registry.crawl_log
    WHERE registry_key = 'knx' AND status = 'ok'
    ORDER BY run_at DESC LIMIT 1
  );
```

**Bug đã tìm và sửa khi test:** bản đầu dùng `first_seen_at >= <giờ Python lúc script bắt
đầu>` — lệch ~1-2ms so với `first_seen_at` (dùng `now()` của Postgres) do 2 đồng hồ khác
nguồn (script vs DB container), khiến device mới bị bỏ sót khỏi kết quả dù insert đúng. Sửa
bằng cách lấy mốc `run_at` từ chính `now()` của Postgres ngay trong transaction ghi device —
chi tiết ở [A2-knx-crawler.md](A2-knx-crawler.md). Đây là lý do query trên dùng subquery
`SELECT run_at FROM registry.crawl_log` thay vì truyền timestamp từ bên ngoài vào.

Nếu brand crawl về không khớp gì (kể cả alias) → không lọt vào digest, nhưng **nên log lại
riêng** những brand "lạ" xuất hiện nhiều lần — có thể là brand đáng thêm vào danh sách quan
tâm mà chưa ai để ý. Đề xuất: view đơn giản, không cần bảng mới:

```sql
CREATE VIEW registry.unmatched_brands AS
SELECT brand, count(*) AS device_count, max(first_seen_at) AS last_seen
FROM registry.devices d
WHERE NOT EXISTS (
  SELECT 1 FROM registry.brands_of_interest b
  WHERE b.is_active
    AND (lower(d.brand) = lower(b.brand)
         OR lower(d.brand) = ANY (SELECT lower(a) FROM unnest(b.aliases) a))
)
GROUP BY brand
ORDER BY device_count DESC;
```

Tùng xem view này định kỳ (không cần tự động hóa ở giai đoạn này) để quyết định có thêm
brand mới vào danh sách quan tâm không.

## Definition of Done

- [ ] `registry.brands_of_interest` có ít nhất seed thật từ Tùng (không phải data giả) —
      vẫn đang chờ (câu hỏi #4 overview)
- [x] Query match brand chạy đúng — test bằng brand thật ("ABB", "Panasonic") trên 4.948
      thiết bị CSA Matter thật + 2 thiết bị giả lập, match chính xác, không lẫn thiết bị cũ
- [ ] `registry.unmatched_brands` — viết rồi nhưng chưa test riêng (chưa có seed
      `brands_of_interest` thật để tạo tình huống "brand lạ" có ý nghĩa)
- [x] Test trên dữ liệu thật: đã dùng toàn bộ 4.948 thiết bị CSA Matter thật, không phải
      data giả lập hoàn toàn — chỉ 2 thiết bị match thêm vào là giả lập để tạo tình huống test
