# A4 — Crawler CSA Matter certified DB

Ước tính: 5-8h (rủi ro lệch cao nhất trong Track A) · Phụ thuộc: A1 · Xem [00-overview.md](00-overview.md).

## Mục tiêu

Tương tự A2 nhưng cho CSA Matter certified product database, ghi vào cùng
`registry.devices`/`registry.snapshots` với `registry_key = 'matter_csa'`. Toàn bộ logic
UPSERT, anomaly check, crawl_log dùng lại y hệt A2 — khác biệt duy nhất là nguồn dữ liệu.

## Chưa xác định — cần research spike trước khi ước tính giờ chính xác

Kế hoạch gốc không ghi rõ URL/API của CSA Matter DB. Trước khi code, cần trả lời:

1. Trang certified product của CSA IoT có API công khai hay chỉ có giao diện web
   (phải scrape HTML)?
2. Có phân trang không, bao nhiêu sản phẩm/trang, tổng bao nhiêu sản phẩm Matter hiện tại?
3. Có anti-bot (Cloudflare challenge, rate limit theo IP) không? — nếu có, đây là rủi ro
   giống hệt rủi ro đã ghi trong `knx-news-agent-plan.md` §9.1 (mục 3, Playwright ARM64) và
   §12 ("extract fail cao trên site TQ") — chỉ khác đối tượng.
4. Trường dữ liệu nào lấy được: brand, model, category, device_type, cert_date — CSA có
   phân loại "device type" theo chuẩn Matter không (light, lock, thermostat...)? Field này
   cần cho `registry.devices.device_type`.

**Đề xuất: dành 1-2h đầu của estimate 5-8h làm research spike (không viết code), xác nhận
lại 4 điểm trên, rồi mới chốt cách làm** (API trực tiếp / HTML scrape / cần Playwright).
Nếu cần Playwright do anti-bot, cân nhắc dùng chung container `news-renderer` (Track B, §9.1)
thay vì dựng thêm container riêng cho Track A — tiết kiệm RAM, nhưng tạo phụ thuộc chéo sang
Track B mà §2.3 vốn muốn tránh. Quyết định này nên chờ đến khi Track B thực sự build
container đó, không dựng riêng sớm cho một crawler chạy 1 lần/tuần.

## Hành vi (giống A2, khác nguồn)

```
Fetch danh sách Matter-certified products (toàn bộ, hoặc lọc theo category liên quan tới
smart home/building automation nếu CSA có phân loại — không cần crawl category không liên
quan như appliance nếu KNXStore không bán mảng đó, cần Tùng xác nhận phạm vi category)
  │
  ▼
Cùng flow UPSERT / anomaly check / crawl_log như A2, registry_key = 'matter_csa'
```

## Definition of Done

- [ ] Research spike trả lời được 4 câu hỏi ở trên, ghi lại kết quả (cập nhật file này)
- [ ] Crawler chạy 1 lần, ghi đúng số lượng sản phẩm vào `registry.snapshots`
      (registry_key = 'matter_csa')
- [ ] Cùng bộ test case anomaly/duplicate như A2, áp dụng cho `matter_csa`
- [ ] Nếu cần Playwright: quyết định dùng chung hay tách riêng container đã được ghi lại
      rõ ràng, không để ngầm định
