# Nguồn tham khảo content — Track B

Ghi nhận nguồn thô do Tùng thu thập (2026-08-14), chưa qua triage/dedupe của Track B. Dùng làm input seed cho `sources.yaml` (B0).

## Kết quả kiểm tra URL (2026-08-14)

Test bằng `curl` (HTTP status + follow redirect + UA trình duyệt thật), không phải extractor thật của B1 — chỉ smoke-test sống/chết. 54 URL:

| Trạng thái | Số lượng | Ý nghĩa |
|---|---|---|
| ✅ OK | 38 | 200, nội dung tải được bình thường |
| ⚠️ Chặn bot | 8 | 403 hoặc 200 nhưng là trang JS-challenge (Incapsula/Cloudflare) — cần renderer (B6) hoặc bỏ qua |
| ❌ Chết | 5 | DNS fail, 404, hoặc 521 origin down — nên loại khỏi seed |

Fail rate thô (chặn + chết) = 13/54 ≈ **24%** — cao hơn ngưỡng DoD của B1 (<20%), tập trung ở 2 cụm: security/lighting trade magazine EN (chặn bot mạnh: Incapsula, Cloudflare) và blog TQ CSDN/Zhihu (chặn bot + 1 domain chết hẳn).

### ❌ Chết — loại khỏi seed hoặc tìm link thay thế

| Link | Lỗi | Ghi chú |
|---|---|---|
| https://www.houndsecurity.co.uk/post/bs-en-50131-intruder-alarm-compliance | DNS không phân giải được | Domain có vẻ đã ngừng hoạt động |
| https://www.sohu.com/a/979369718_122515144 | Redirect → `/404.html` | Bài đã bị gỡ khỏi Sohu |
| https://blog.csdn.net/QZX040923/article/details/148919961 | Connection timeout | Không phản hồi sau 15s, thử lại vẫn fail |
| https://blog.csdn.net/weixin_36064575/article/details/154411342 | Connection timeout | Không phản hồi sau 15s, thử lại vẫn fail |
| https://blog.csdn.net/weixin_42612405/article/details/152235576 | HTTP 521 (Cloudflare: origin server down) | Server gốc đang down, có thể tạm thời — thử lại sau vài ngày |

### ⚠️ Chặn bot — cần renderer/headless hoặc chấp nhận bỏ qua

| Link | Mã | Ghi chú |
|---|---|---|
| https://www.buildings.com/building-systems-om/lighting/article/55257331/... | 403 | |
| https://www.buildings.com/smart-buildings/article/33017724/... | 403 | |
| https://www.arch-products.com/architectural-lighting/article/55092739/... | 403 | |
| https://norbain.com/news/a-guide-to-intruder-alarm-grading | 403 | |
| https://thundersaidenergy.com/downloads/building-automation-energy-savings-knx-case-studies-and-leading-companies/ | 403 | |
| https://zhuanlan.zhihu.com/p/130692312 | 403 | Zhihu chặn bot gần như tuyệt đối, cần renderer hoặc RSS bridge |
| https://zhuanlan.zhihu.com/p/144902191 | 403 | Tương tự trên |
| https://www.securityinformed.com/news/dnake-knx-smart-building-automation... | 200 nhưng là trang Incapsula JS-challenge | Không lấy được nội dung thật dù status 200 — cần bóc tách kỹ khi build B1 |

## DALI-2

| Tiêu đề | Link | Nguồn | Loại | Năm | Trạng thái | Ghi chú |
|---|---|---|---|---|---|---|
| Standards Harmonization Drives Interoperability for Lighting Control | https://www.buildings.com/building-systems-om/lighting/article/55257331/standards-harmonization-drives-interoperability-for-lighting-control | Buildings.com | Trade Magazine | 2021 | ⚠️ 403 | Multi-standard interoperability — lý luận chọn DALI-2 certified |
| DALI+ Platform Delivers Lighting Control with Wireless and IP Networking | https://www.buildings.com/smart-buildings/article/33017724/dali-platform-delivers-dali-lighting-control-with-wireless-and-ip-based-networking | Buildings.com | Industry News | 2022 | ⚠️ 403 | DALI+ (wireless + IP) — hướng đi tiếp theo của DALI Alliance |
| DALI Lighting Control Protocol: All You Need to Know | https://www.knxhub.com/dali-lighting-control-protocol-and-future-explained/ | KNXHub | Technical Guide | 2025 | ✅ OK | DALI-1 → DALI-2 → D4i → IoT-ready — bài explainer toàn diện |
| Smart Lighting Control with DALI and D4i | https://www.arch-products.com/architectural-lighting/article/55092739/smart-lighting-control-with-dali-and-d4i | Architectural Products | Trade Magazine | 2024 | ⚠️ 403 | DALI + D4i energy reporting — tạp chí kiến trúc B2B, góc nhìn specifier |
| DALI D4i Smart Luminaires — Energy Reporting & IoT Integration | https://www.knxhub.com/dali-d4i-smart-luminaires/ | KNXHub | Technical Guide | 2025 | ✅ OK | D4i: energy monitoring tới từng luminaire, predictive maintenance, IoT cloud |
| Advanced DALI Energy Management — Smart Lighting Optimization | https://www.knxhub.com/advanced-dali-energy-management/ | KNXHub | Technical Guide | 2025 | ✅ OK | Daylight harvesting, occupancy scheduling, energy dashboard — B2B energy case |
| New Controller Makes DALI-2 Accessible for Every Lighting Project | https://www.electropages.com/2025/10/new-controller-makes-dali-2-accessible-every-lighting-project | Electropages | Product News | 2025 | ✅ OK | Controller DALI-2 mới Oct 2025 — tin sản phẩm B2B, dùng cho bài ra mắt |
| D4i & DALI-2: LED Data Management for Smart Buildings | https://tillumelight.com/en/blogs/dali-2-series/d4i-dali-2-intelligent-lighting-data-management | TILLUME | Technical Article | 2025 | ✅ OK | D4i vs DALI-2 phân biệt rõ ràng, IEC 62386-251 — bài kỹ thuật tốt |

## Satel

| Tiêu đề | Link | Nguồn | Loại | Năm | Trạng thái | Ghi chú |
|---|---|---|---|---|---|---|
| BS EN 50131: Intruder Alarm Compliance Guide 2025 | https://www.houndsecurity.co.uk/post/bs-en-50131-intruder-alarm-compliance | Hound Security Systems | Compliance Guide | 2025 | ❌ DNS fail | Grade 1-4 compliance — nền cho bài tư vấn chọn Satel theo rủi ro |
| Intruder Alarm Grades Explained (Updated 2025) | https://norbain.com/news/a-guide-to-intruder-alarm-grading | Norbain (distributor) | Buyer Guide | 2025 | ⚠️ 403 | Giải thích Grade 1→4 theo use case — dùng cho bài so sánh dòng Satel |
| EN50131 Guide – Intruder Alarm Grades Made Simple | https://www.businesswatchgroup.co.uk/en50131-guide-intruder-alarm-grades-made-simple/ | Business Watch Group | Installer Guide | 2024 | ✅ OK | Ngắn gọn, rõ ràng — tham khảo khi viết bài cho ME contractor |
| Integrated Security and Automation Solutions from SATEL at Security Expo Berlin 2025 | https://euro-security.de/en/integrated-security-and-automation-solutions-from-satel-at-security-expo-berlin-2025/ | Euro Security (DE) | Industry News | 2025 | ✅ OK | Satel tại Security Expo Berlin 2025 — tin ngành, sản phẩm mới, building automation |
| Satel Integration Module for INTEGRA Panel and KNX Automation System | https://intelibus.co.uk/product/satel-integration-module-for-integra-panel-and-knx-automation-system/ | Intelibus UK | Product / SI Resource | 2024 | ✅ OK | INT-KNX-2: tích hợp INTEGRA + KNX — bài sản phẩm cho SI cần tích hợp 2 hệ thống |
| SATEL Smart Security Systems: The Next Generation of Protection | https://www.freewaves.com.cy/satel-smart-security-systems-the-next-generation-of-protection-for-homes-and-businesses/ | FreeWaves (Satel partner) | Partner Blog | 2025 | ✅ OK | INTEGRA cho commercial buildings — góc nhìn partner/distributor |

## KNX

| Tiêu đề | Link | Nguồn | Loại | Năm | Trạng thái | Ghi chú |
|---|---|---|---|---|---|---|
| 2026 Update on KNX Systems: 7 Most Demanded Automation Scenarios in Homes and Offices | https://www.makel.com.tr/en/blog/smart-home-technologies/2026-update-on-knx-systems-7-most-demanded-scenarios-in-homes-and-offices | Makel (manufacturer) | Technical Article | 2026 | ✅ OK | 7 kịch bản KNX thực tế phổ biến nhất — tham khảo cho bài use case |
| Building Automation: AI, KNX and Smart Energy Savings — Case Studies | https://thundersaidenergy.com/downloads/building-automation-energy-savings-knx-case-studies-and-leading-companies/ | Thunder Said Energy | Market Research | 2025 | ⚠️ 403 | Tiết kiệm 30-35% energy với KNX+AI, ROI 2 năm — số liệu thuyết phục cho bài B2B |
| KNX in 2025: Top Trends Driving Smart Building Innovation | https://knxman.com/2025/04/03/knx-in-2025-top-trends-driving-smart-building-innovation/ | KNXMAN | Industry Trends | 2025 | ✅ OK | KNX Secure, IoT, AI, sustainability — tổng hợp xu hướng 2025 cho SI |
| Smart Buildings and Automation: How BMS & KNX Systems Reduce Energy Costs | https://msselectronics.gr/en/smart-buildings-reduce-energy-costs/ | MSS Electronics | SI Blog | 2025 | ✅ OK | BMS + KNX giảm chi phí vận hành — bài tư vấn ROI cho chủ đầu tư |
| DNAKE KNX For Seamless Smart Building Automation | https://www.securityinformed.com/news/dnake-knx-smart-building-automation-co-1563951456-ga-npr.1781757521.html | Security Informed | Industry News | 2025 | ⚠️ 200 (JS-challenge) | Tích hợp KNX + an ninh + intercom — bài tin ngành B2B |

## Casambi

| Tiêu đề | Link | Nguồn | Loại | Năm | Trạng thái | Ghi chú |
|---|---|---|---|---|---|---|
| Lighting Controls Explained: Casambi, Scene Setting and What Specifiers Need to Know | https://detaillighting.co.uk/lighting-controls-explained-casambi-scene-setting-and-what-specifiers-need-to-know/ | Detail Lighting UK | Specifier Guide | 2025 | ✅ OK | Góc nhìn lighting specifier — so sánh Casambi vs DALI, scene control, tender spec |
| Casambi for Hospitality — Wireless Lighting for Hotels and Restaurants | https://casambi.us/hospitality/ | Casambi US | Solution Page | 2025 | ✅ OK | Use case hospitality cụ thể — tham khảo cho bài khách sạn/nhà hàng |
| Casambi Specification Guide — Full Tender Text and CAD Files | https://casambi.com/specification-with-casambi/ | Casambi | Specifier Resource | 2025 | ✅ OK | Tender text chuẩn cho dự án — dùng khi tư vấn cho ME contractor/specifier |

## 🇨🇳 Nguồn CN

| Tiêu đề | Link | Nguồn | Loại | Năm | Trạng thái | Ghi chú |
|---|---|---|---|---|---|---|
| 2026年智能照明控制系统行业洞察：从硬件到平台，专业供应商选型与落地实践 | https://www.sohu.com/a/1051913121_122155969 | 搜狐 Sohu | Industry Insight | 2026 | ✅ OK | KNX vs các hệ thống TQ, DALI gateway thị trường — tham khảo B2B positioning |
| 2026年 DALI调光网关厂家推荐：智能照明控制系统核心技术与市场口碑深度解析 | https://www.sohu.com/a/979369718_122515144 | 搜狐 Sohu | Market Analysis | 2026 | ❌ 404 (redirect) | DALI gateway landscape TQ 2026 — bài đã bị gỡ, cần tìm nguồn thay thế |
| 智能楼宇里解题关键：DALI协议与KNX协议融合的转换网关 | https://www.sohu.com/a/958742372_121681516 | 搜狐 Sohu | Technical Article | 2025 | ✅ OK | KNX+DALI gateway kiến trúc phần mềm/phần cứng — tham khảo kỹ thuật tích hợp |
| 浅谈智能照明系统KNX与DALI协议网关的应用 | https://www.sohu.com/a/734721093_121248877 | 搜狐 Sohu | Technical Article | 2024 | ✅ OK | Ứng dụng gateway KNX-DALI trong chiếu sáng thông minh |
| KNX协议智能调光照明系统（一） | https://zhuanlan.zhihu.com/p/130692312 | 知乎 Zhihu | Technical Guide | 2020 | ⚠️ 403 | KNX dimming system overview — nền tảng kỹ thuật, nhiều lượt xem |
| 基于KNX总线的社区智能照明系统应用 | https://zhuanlan.zhihu.com/p/144902191 | 知乎 Zhihu | Case Study | 2020 | ⚠️ 403 | Dự án chiếu sáng cộng đồng dùng KNX — case study thực tế TQ |
| KNX：智能家居与楼宇自动化的开放标准 | https://blog.csdn.net/QZX040923/article/details/148919961 | CSDN | Technical Article | 2025 | ❌ Timeout | KNX open standard ISO/IEC 14543 — bài kỹ thuật mới 2025 |
| 智能照明系统中KNX与DALI协议网关设计与实现 | https://blog.csdn.net/weixin_42612405/article/details/152235576 | CSDN | Technical Article | 2025 | ❌ 521 origin down | Thiết kế gateway KNX-DALI chi tiết — rất kỹ thuật, dành cho SI |
| KNX总线协议详解与智能建筑应用实战 | https://blog.csdn.net/weixin_36064575/article/details/154411342 | CSDN | Technical Guide | 2025 | ❌ Timeout | KNX protocol deep dive + ứng dụng thực chiến tòa nhà thông minh |

## Matter Smarthome (đã phân loại)

Nhóm B2C, đã fetch nội dung thật (WebFetch) để xác định loại trang — không chỉ dừng ở HTTP status. Tổng 23 link: **10 Article**, **11 Listing/Category**, **2 lỗi** (không lấy được nội dung thật dù URL "sống").

| Link | Loại trang | Tiêu đề / Mô tả | Kind | Ghi chú |
|---|---|---|---|---|
| https://www.the-ambient.com/news/smart-home/ | Listing | Feed tin tức smart home, chronological, phân trang | News (category feed) | Nguồn tin nhanh đa hãng (Google/Apple/Philips/Amazon), tốt để theo dõi xu hướng |
| https://www.the-ambient.com/news/matter/ | Listing | Feed tin tức riêng về Matter (update version 1.3→1.6, thiết bị mới), 7 trang | News (category feed) | Nguồn tin Matter chuyên biệt — giá trị nhất trong nhóm The Ambient |
| https://www.the-ambient.com/reviews/ | Listing | Reviews thiết bị smart home đã test, 25 trang | Review (category feed) | Nguồn đánh giá sản phẩm đã kiểm chứng — dùng cho content so sánh sản phẩm |
| https://www.tomsguide.com/home/smart-home/news | **Không dùng được** | Redirect ra trang marketing "Tom's Guide Club" (đăng ký email), không phải feed tin tức | — | URL không trỏ đúng nội dung mong đợi — loại khỏi seed, cần tìm URL category đúng |
| https://www.androidcentral.com/accessories/smart-home | Listing | Category smart home: bài nổi bật + ~10 bài mới nhất, phân trang 2-9 | News | Thiên về hệ sinh thái Google Home/Gemini, ok làm nguồn tin sản phẩm |
| https://www.engadget.com/category/smart-home-reviews/ | Listing | Category reviews smart home, nhưng chỉ 2 bài hiển thị (review thưa) | Review | Độ phủ thấp — cân nhắc bỏ hoặc theo dõi thêm |
| https://www.digitaltrends.com/home/ | **Lỗi** | Fetch 2 lần đều trả về rỗng — nghi JS-render hoặc chặn bot dù HTTP 200 | — | Cần renderer (Playwright, B6) để xác nhận, không kết luận được qua WebFetch |
| https://staceyoniot.com/tag/smart-home/ | Listing | Tag archive, 73 trang, ~5 bài/trang (Home Assistant, Zigbee vs Matter, LiFi...) | News/Analysis | Nguồn phân tích IoT chuyên sâu, chất lượng kỹ thuật tốt |
| https://www.home-assistant.io/blog/ | Listing | Blog index chính thức Home Assistant — release notes, đối tác, community | Blog/Release Notes | Nguồn chính thức open-source ecosystem, độ tin cậy cao |
| https://research.samsung.com/blog/CSA-Matter-1-6-... | **Article** | "CSA Matter 1.6 Release: Ambient Sensing, More Intuitive Setup, Multi-Ecosystem Experiences, and Context-Driven Control" | Technical/Press | Chi tiết kỹ thuật chính thức về Matter 1.6 — nguồn uy tín cao |
| ~~https://csa-iot.org/newsroom/page/4/~~ → **https://csa-iot.org/newsroom/** (đã sửa 2026-08-14, URL gốc trỏ nhầm trang 4 thay vì trang mới nhất) | Listing | Newsroom chính thức CSA — press release, blog, video, filter theo Matter/Zigbee/Aliro, 212 trang | News (official) | Nguồn chính thức uy tín nhất cho tin chuẩn Matter |
| https://blog.matterhubs.com/matter-hubs/ | **Article** | "10 Best Matter Supported Smart Hubs 2026" | Review/Buyer Guide | So sánh hub Matter — nội dung B2C thuần, không nhắc KNX/BACnet; là **đối thủ content trực tiếp**, có thể dùng làm bài đối chiếu "Matter vs KNX" |
| https://blog.matterhubs.com/tapo-smart-plug-mini/ | **Article** | "Tapo Smart Plug Mini - Matter Supported" | Product Review | Review sản phẩm giá rẻ, dùng tham khảo phân khúc entry-level |
| https://blog.matterhubs.com/evehome-matter-devices/ | **Article** | "Matter Compatible EveHome Smart Devices" | Product Review | Review dòng thiết bị EveHome (5 sản phẩm) |
| https://matter-smarthome.de/en/practice/ | Listing | Category "Practice" — hướng dẫn thực hành Matter (~13 bài, tác giả Frank-Oliver Grün) | Technical Guide (category) | Nguồn hướng dẫn thực hành tốt cho technical content |
| https://matter-smarthome.de/en/development/ (+ page/3, /4, /5) | Listing | Cùng 1 category "Development" — roadmap Matter, gồm cả bài **KNX IoT + Matter integration** | News/Technical (category) | 4 URL trỏ cùng category, khác trang phân trang — chỉ cần theo dõi 1 feed, không seed riêng từng page |
| https://blog.smartthings.com/category/matter/ | Listing | Category Matter của SmartThings — tích hợp IKEA/Aqara/Eve, ~6 bài chính | News/Marketing (official) | Nguồn chính thức Samsung, thiên marketing hệ sinh thái SmartThings |
| https://www.theverge.com/22832127/matter-smart-home-products-thread-wifi-explainer | **Lỗi** | WebFetch từ chối fetch domain theverge.com (giới hạn công cụ, không phải lỗi URL) | — | Cần kiểm tra bằng công cụ khác (curl/browser) — đã biết trước đó HTTP 200 |
| https://thinkrobotics.com/blogs/learn/matter-protocol-explained-for-smart-homes-complete-guide-2025 | **Article** | "Matter Protocol Explained for Smart Homes: Complete Guide 2025" | Technical Guide | Bài giải thích Matter toàn diện cho B2C |
| https://www.aqara.com/en/blog/ | Listing | Blog index Aqara: bài blog (Zigbee vs Thread vs Matter...) + case study triển khai lớn (KAFD 10.000+ devices, HAUS UPDATE Nhật Bản) | Blog + Case Study | Rất giá trị — case study quy mô lớn hữu ích cho content B2B lẫn B2C |

**Việc cần làm tiếp:**
- `tomsguide.com` — tìm lại URL category đúng (URL hiện tại redirect sai).
- `digitaltrends.com/home/` và `theverge.com/...` — xác minh bằng công cụ khác (WebFetch không đọc được nội dung), không tự động loại vì HTTP status vẫn 200.
- 4 URL `matter-smarthome.de/en/development/page/N` — gộp thành 1 entry `sources.yaml` (theo dõi category, không phải 4 nguồn riêng).
- Các trang Listing/Category nên khai báo `kind: category-feed` hoặc tương đương trong `sources.yaml` (không phải `article`), vì B1 extractor cần biết để bóc tách danh sách link con thay vì parse như 1 bài.
