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
Match phải qua cả `brand` lẫn `aliases`, không phân biệt hoa thường:

```sql
SELECT d.*
FROM registry.devices d
JOIN registry.brands_of_interest b
  ON b.is_active
 AND (
      lower(d.brand) = lower(b.brand)
      OR lower(d.brand) = ANY (SELECT lower(a) FROM unnest(b.aliases) a)
     )
WHERE d.registry_key = 'knx'
  AND d.first_seen_at >= <thời điểm crawl lần này>;
```

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

- [ ] `registry.brands_of_interest` có ít nhất seed thật từ Tùng (không phải data giả)
- [ ] Query match brand chạy đúng trên ví dụ: device brand = "ABB i-bus KNX", alias trong
      bảng = "ABB i-bus" → match được (kiểm tra matching theo substring/alias, không chỉ
      exact — nếu case test này fail thì cần đổi từ `=` sang `ILIKE '%' || alias || '%'`,
      quyết định cụ thể sau khi có dữ liệu brand thật, vì exact-match alias an toàn hơn
      substring nhưng dễ bỏ sót biến thể tên)
- [ ] `registry.unmatched_brands` trả về đúng danh sách brand không khớp, có count hợp lý
- [ ] Test trên dữ liệu thật từ 1 lần chạy A2: số device match brand quan tâm khớp với đếm
      thủ công trên vài dòng mẫu
