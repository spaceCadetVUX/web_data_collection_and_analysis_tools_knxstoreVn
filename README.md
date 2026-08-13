# KNX News Intelligence Agent

Dự án của KNXStore.vn: thu thập, lọc và tổng hợp thông tin ngành building automation
(KNX, DALI-2, Matter/CSA, BACnet) phục vụ quyết định sản phẩm/phân phối và content marketing.

## Cấu trúc

```
.
├── docs/
│   ├── plan.md                    Kế hoạch tổng v1.1 — kiến trúc, chi phí, data model, rủi ro
│   └── pipeline-overview.html     Sơ đồ trực quan toàn bộ pipeline (mở bằng trình duyệt)
└── track-a/                       Registry Diff — track đang build, xem track-a/README.md
```

## Trạng thái

| Track | Mô tả | Trạng thái |
|---|---|---|
| A — Registry Diff | Phát hiện thiết bị KNX/Matter mới qua registry chứng nhận, không dùng LLM | Đang build — xem [track-a/README.md](track-a/README.md) |
| B — News Pipeline | Thu thập + phân tích tin tức bằng Claude Haiku 4.5 | Chưa build. Tùng đang tự tìm nguồn uy tín để crawl bài viết (thay cho `sources.yaml` mẫu ở `docs/plan.md` §7), sẽ đưa vào khi build |
| C — Marketing Inspiration | Mining nội dung XHS/WeChat cho content angle | Chưa build |

Chi tiết đầy đủ: [`docs/plan.md`](docs/plan.md).
