# A5 — n8n workflow weekly + gửi Zalo

Ước tính: 2-3h · Phụ thuộc: A3 · Xem [README.md](README.md).

## Trạng thái (2026-08-13)

Đã build xong workflow **"A5 Registry Diff Digest"** trong n8n-dev (`localhost:5678`), test
bằng data thật (3.865 thiết bị baseline khớp brand quan tâm). Còn lại **placeholder gửi Zalo**
— xem mục "Việc chưa giải quyết" ở cuối file, cần xử lý trước khi coi A5 là "hoàn tất thật".

## Mục tiêu

Nối A3 (query diff) thành 1 workflow n8n chạy weekly, gửi kết quả qua Zalo KHub. **Khác với sơ
đồ gốc bên dưới:** crawler A2/A4 **không** chạy từ n8n — đã chốt chạy qua `launchd` trên host
(xem `run_weekly_crawl.sh`), ghi thẳng Postgres. n8n chỉ làm phần query diff + format + gửi.
Lý do: tránh phải mount Docker socket vào n8n-dev (rủi ro bảo mật không tương xứng lợi ích ở
quy mô team 5 người) hoặc tự build custom n8n image có Python.

## Kênh Zalo = KHub — quyết định bởi Vũ (2026-08-13), chưa qua Tùng

Theo bối cảnh tổ chức: **Zalo Hotline (Pancake) là kênh sales thực, xử lý cẩn thận, không
gửi tin nhắn tự động trừ khi được xác nhận rõ ràng.** Digest Registry Diff là tin nhắn tự
động định kỳ — về nguyên tắc **không nên** đi qua Zalo Hotline.

`KHub` là chatbot kênh riêng biệt với sales Hotline — phù hợp hơn cho việc này.

**Ghi chú quan trọng:** tài liệu gốc yêu cầu xác nhận từ **Tùng** trước khi chốt kênh này
("quyết định phải chốt trước, không suy luận thay được"). Trong phiên làm việc 2026-08-13,
**Vũ tự quyết định** chọn KHub (không phải Hotline) khi được hỏi lại — Claude đã hỏi rõ liệu
đây có phải Tùng confirm hay Vũ tự quyết, Vũ xác nhận là tự quyết. Ghi lại đúng như vậy, không
gán nhầm là "Tùng đã confirm". Nên Tùng xem lại quyết định này khi có thời gian.

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

**Cập nhật 2026-08-13 — Vũ tự quyết (chưa qua Tùng):** khi 0 device match, workflow **vẫn gửi**
tin "không có thiết bị mới" (không im lặng). Đây là quyết định ngược lại với đề xuất kỹ thuật
ban đầu ở trên — đề xuất ban đầu lo rủi ro "alert fatigue" (kế hoạch chính §12: tin lặp đi lặp
lại "không có gì mới" làm mất thói quen đọc). Lý do cụ thể của Vũ cho lựa chọn ngược lại chưa
được ghi lại trong phiên làm việc này — cần hỏi lại khi review. Tùng nên xem lại cả 2 quyết
định (kênh + hành vi 0-match) khi có thời gian — cả hai hiện tại là quyết định của Vũ, không
phải Tùng.

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

- [x] Xác nhận kênh gửi = Zalo KHub (không phải Hotline/Pancake) — **quyết định bởi Vũ**,
      chưa qua Tùng, xem cảnh báo ở mục trên
- [x] Schedule Trigger weekly đúng lịch (Monday 8am, timezone `Asia/Ho_Chi_Minh` — set ở
      workflow Settings, vì n8n-dev mặc định `America/New_York`), test bằng trigger thủ công
- [ ] Cả A2 và A4 fail hoặc anomaly → workflow không gửi tin, có log lỗi trong n8n — **chưa
      làm**, node If hiện tại chỉ check "0 match", chưa check `registry.crawl_log.status`
- [x] 0 device match brand quan tâm → **gửi** "không có gì mới" (không im lặng) — quyết định
      bởi Vũ, xem cảnh báo ở mục trên
- [ ] Test end-to-end thật: seed 1 device mới giả trong `registry.devices` → chạy workflow →
      tin nhắn tới đúng KHub, nội dung đúng format — **chưa làm được**, xem mục dưới
- [x] Query diff + format message test bằng data thật (3.865 thiết bị baseline) trong n8n-dev

## Việc chưa giải quyết (2026-08-13)

1. **Gửi Zalo KHub thật — chưa build được.** `docs/plan.md` (dòng 56/113/671) ghi delivery là
   "Zalo KHub **MCP**", và orchestrator production nằm ở `n8n.tungvu.vn` — khác hẳn n8n-dev
   đang chạy trong `track-a/src/docker-compose.yml` (không có credential KHub thật, theo đúng
   comment trong file đó). Workflow trong n8n-dev hiện dừng ở node format message, **chưa có
   node gửi thật** — cần đặt placeholder rồi export JSON, import qua `n8n.tungvu.vn` sau, hoặc
   build trực tiếp ở đó nếu có quyền truy cập.
2. **launchd chạy crawler tự động — chưa hoạt động.** `com.knxstore.registry-weekly-crawl.plist`
   đã tạo và load, nhưng bị macOS TCC chặn: `/bin/bash: run_weekly_crawl.sh: Operation not
   permitted` (không có quyền vào `~/Desktop`). Cần tự cấp **Full Disk Access cho `/bin/bash`**
   trong System Settings → Privacy & Security, nếu không launchd sẽ tiếp tục chết mỗi lần chạy
   theo lịch (Chủ nhật 02:00). Chạy tay qua `bash run_weekly_crawl.sh` vẫn hoạt động bình
   thường (không bị TCC chặn khi chạy từ Terminal/session đã cấp quyền).
3. **Node If mới check "0 match", chưa check crawl fail/anomaly.** DoD gốc yêu cầu: nếu A2/A4
   fail hoặc `aborted_anomaly` (xem A2) thì không gửi digest, có log lỗi. Chưa build — cần
   thêm điều kiện query `registry.crawl_log.status != 'ok'` trước khi coi "0 match" là thật.
4. **Cả 2 quyết định ở trên (kênh, hành vi 0-match) là Vũ tự quyết, chưa qua Tùng** — theo
   đúng tinh thần "quyết định phải chốt trước, không suy luận thay được" trong tài liệu gốc,
   nên đưa lại cho Tùng xác nhận khi có thời gian, trước khi Publish workflow.
