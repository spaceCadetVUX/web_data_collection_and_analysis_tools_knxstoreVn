# A5 — n8n workflow weekly + gửi Zalo

Ước tính: 2-3h · Phụ thuộc: A3 · Xem [00-overview.md](00-overview.md).

## Mục tiêu

Nối A2, A4, A3 thành 1 workflow n8n chạy weekly, gửi kết quả qua **Zalo Hotline (Pancake)**
hoặc **Zalo KHub** — cần chốt kênh nào (xem cảnh báo bên dưới).

## ⚠️ Chọn kênh Zalo — không tự ý dùng Zalo Hotline

Theo bối cảnh tổ chức: **Zalo Hotline (Pancake) là kênh sales thực, xử lý cẩn thận, không
gửi tin nhắn tự động trừ khi được xác nhận rõ ràng.** Digest Registry Diff là tin nhắn tự
động định kỳ — về nguyên tắc **không nên** đi qua Zalo Hotline.

`KHub` là chatbot kênh riêng biệt với sales Hotline — phù hợp hơn cho việc này. Trước khi
build A5, xác nhận với Tùng: digest Track A gửi qua **Zalo KHub**, không phải Hotline/Pancake.
Đây là quyết định phải chốt trước, không suy luận thay được.

## n8n workflow

```
Cron trigger (weekly, ví dụ thứ 2 hàng tuần)
  │
  ├──► Trigger crawler KNX (A2)      ──┐
  ├──► Trigger crawler Matter (A4)   ──┤
  │                                    ▼
  │                          Chờ cả 2 xong (không gửi digest nếu 1 trong 2 fail
  │                          hoặc rơi vào aborted_anomaly — xem A2)
  │                                    │
  │                                    ▼
  │                          Query diff theo brands_of_interest (A3)
  │                                    │
  │                          0 device match?
  │                         ┌──────────┴──────────┐
  │                        Có                    Không
  │                         │                      │
  │                    Không gửi tin          Format message
  │                    (tránh alert                │
  │                    fatigue — cần                ▼
  │                    Tùng xác nhận)      Gửi qua Zalo KHub MCP
```

**Quyết định "0 match thì không gửi"** là đề xuất kỹ thuật, chưa phải quyết định của Tùng —
tránh lặp lại đúng rủi ro đã ghi trong kế hoạch chính §12 ("digest bị bỏ đọc"): nếu tuần nào
cũng nhận được tin "không có gì mới", thói quen đọc sẽ mất nhanh hơn. Cần Tùng xác nhận đồng ý
trước khi implement theo hướng này.

## Format tin nhắn (đề xuất)

```
🔔 Registry Diff — tuần [ngày bắt đầu] đến [ngày kết thúc]

KNX (3 thiết bị mới):
• ABB — [model] — [category] — cert [ngày]
• JUNG — [model] — [category] — cert [ngày]

CSA Matter (1 thiết bị mới):
• GVS — [model] — cert [ngày]
```

Không dùng emoji tràn lan — 1 emoji đầu dòng tiêu đề là đủ, giữ tinh thần "không bọc đường,
đi thẳng vào dữ liệu" của tổ chức.

## Definition of Done

- [ ] Xác nhận kênh gửi = Zalo KHub (không phải Hotline/Pancake) — ghi lại quyết định ở đây
      sau khi Tùng confirm
- [ ] Cron chạy đúng lịch weekly, test bằng cách trigger thủ công trong n8n
- [ ] Cả A2 và A4 fail hoặc anomaly → workflow không gửi tin, có log lỗi trong n8n
- [ ] 0 device match brand quan tâm → hành vi (gửi "không có gì mới" hay im lặng) đã được
      Tùng xác nhận, không phải mặc định tự chọn
- [ ] Test end-to-end: seed 1 device mới giả trong `registry.devices` (brand thuộc
      `brands_of_interest`) → chạy workflow → tin nhắn tới đúng KHub, nội dung đúng format
