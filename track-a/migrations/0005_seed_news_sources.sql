-- Seed news.sources từ docs/sources-content-research.md (test 2026-08-14).
--
-- CHỈ seed nguồn đã xác nhận đọc được nội dung thật — loại khỏi 54 URL gốc:
--   - 5 nguồn chết (DNS fail / 404 / 521 origin down)
--   - 8 nguồn chặn bot (403 hoặc JS-challenge Incapsula/Cloudflare) — cần renderer (B6),
--     xem mục "Chặn bot" trong sources-content-research.md
--   - 3 nguồn Matter Smarthome không dùng được: tomsguide.com (redirect sai sang trang
--     marketing), digitaltrends.com/home/ và theverge.com (không xác minh được nội dung
--     thật, để đó chờ kiểm tra bằng công cụ khác)
--   - 3 URL phân trang matter-smarthome.de/en/development/page/{3,4,5} — gộp chung vào
--     1 nguồn duy nhất (/en/development/), không seed riêng từng trang
--
-- Kết quả: 35 nguồn (không phải 38 như số tổng hợp ghi ở đầu file .md — con số 38 đó là
-- lỗi cộng dồn từ lúc chưa đối chiếu xong nhóm Matter Smarthome, xem lại nếu cần sửa).

INSERT INTO news.sources (slug, name, kind, url, lang, region, category, tier, notes) VALUES

-- DALI-2
('knxhub-dali-lighting-control-protocol', 'KNXHub — DALI Lighting Control Protocol Explained', 'manual', 'https://www.knxhub.com/dali-lighting-control-protocol-and-future-explained/', 'en', 'global', 'media', 2, 'DALI-1 → DALI-2 → D4i → IoT-ready, bài explainer toàn diện'),
('knxhub-dali-d4i-smart-luminaires', 'KNXHub — DALI D4i Smart Luminaires', 'manual', 'https://www.knxhub.com/dali-d4i-smart-luminaires/', 'en', 'global', 'media', 2, 'Energy monitoring tới từng luminaire, predictive maintenance'),
('knxhub-advanced-dali-energy-management', 'KNXHub — Advanced DALI Energy Management', 'manual', 'https://www.knxhub.com/advanced-dali-energy-management/', 'en', 'global', 'media', 2, 'Daylight harvesting, occupancy scheduling, energy dashboard'),
('electropages-dali2-controller-2025', 'Electropages — New Controller Makes DALI-2 Accessible', 'manual', 'https://www.electropages.com/2025/10/new-controller-makes-dali-2-accessible-every-lighting-project', 'en', 'global', 'media', 2, 'Tin sản phẩm controller DALI-2 mới (10/2025)'),
('tillumelight-d4i-dali2-data-management', 'TILLUME — D4i & DALI-2 LED Data Management', 'manual', 'https://tillumelight.com/en/blogs/dali-2-series/d4i-dali-2-intelligent-lighting-data-management', 'en', 'global', 'manufacturer', 2, 'D4i vs DALI-2 phân biệt rõ, IEC 62386-251'),

-- Satel
('businesswatchgroup-en50131-guide', 'Business Watch Group — EN50131 Guide', 'manual', 'https://www.businesswatchgroup.co.uk/en50131-guide-intruder-alarm-grades-made-simple/', 'en', 'UK', 'media', 2, 'Grade 1-4 ngắn gọn — tham khảo bài cho ME contractor'),
('euro-security-satel-expo-berlin-2025', 'Euro Security DE — Satel tại Security Expo Berlin 2025', 'manual', 'https://euro-security.de/en/integrated-security-and-automation-solutions-from-satel-at-security-expo-berlin-2025/', 'en', 'DE', 'media', 2, 'Tin ngành, sản phẩm mới building automation'),
('intelibus-satel-int-knx-2', 'Intelibus UK — Satel INT-KNX-2 Integration Module', 'manual', 'https://intelibus.co.uk/product/satel-integration-module-for-integra-panel-and-knx-automation-system/', 'en', 'UK', 'distributor', 2, 'Tích hợp INTEGRA + KNX — bài cho SI cần ghép 2 hệ'),
('freewaves-satel-smart-security', 'FreeWaves — Satel Smart Security Systems', 'manual', 'https://www.freewaves.com.cy/satel-smart-security-systems-the-next-generation-of-protection-for-homes-and-businesses/', 'en', 'CY', 'distributor', 3, 'Góc nhìn partner/distributor, INTEGRA cho commercial'),

-- KNX
('makel-knx-2026-update-scenarios', 'Makel — 2026 Update on KNX Systems: 7 Scenarios', 'manual', 'https://www.makel.com.tr/en/blog/smart-home-technologies/2026-update-on-knx-systems-7-most-demanded-scenarios-in-homes-and-offices', 'en', 'TR', 'manufacturer', 2, '7 kịch bản KNX thực tế phổ biến nhất'),
('knxman-knx-2025-top-trends', 'KNXMAN — KNX in 2025: Top Trends', 'manual', 'https://knxman.com/2025/04/03/knx-in-2025-top-trends-driving-smart-building-innovation/', 'en', 'global', 'media', 2, 'KNX Secure, IoT, AI, sustainability — tổng hợp xu hướng 2025'),
('msselectronics-bms-knx-energy-costs', 'MSS Electronics — BMS & KNX Reduce Energy Costs', 'manual', 'https://msselectronics.gr/en/smart-buildings-reduce-energy-costs/', 'en', 'GR', 'distributor', 3, 'Bài tư vấn ROI cho chủ đầu tư'),

-- Casambi
('detaillighting-casambi-specifiers', 'Detail Lighting UK — Casambi Scene Setting for Specifiers', 'manual', 'https://detaillighting.co.uk/lighting-controls-explained-casambi-scene-setting-and-what-specifiers-need-to-know/', 'en', 'UK', 'distributor', 2, 'So sánh Casambi vs DALI, scene control, tender spec'),
('casambi-us-hospitality', 'Casambi US — Hospitality Use Case', 'manual', 'https://casambi.us/hospitality/', 'en', 'US', 'manufacturer', 1, 'Use case khách sạn/nhà hàng, chính chủ Casambi'),
('casambi-specification-guide', 'Casambi — Specification Guide (Tender Text)', 'manual', 'https://casambi.com/specification-with-casambi/', 'en', 'global', 'manufacturer', 1, 'Tender text chuẩn, dùng khi tư vấn ME contractor/specifier'),

-- Nguồn CN
('sohu-smart-lighting-industry-insight-2026', '搜狐 — 2026年智能照明控制系统行业洞察', 'manual', 'https://www.sohu.com/a/1051913121_122155969', 'zh', 'CN', 'media', 2, 'KNX vs hệ thống TQ, DALI gateway thị trường'),
('sohu-knx-dali-gateway-integration', '搜狐 — 智能楼宇KNX与DALI协议融合网关', 'manual', 'https://www.sohu.com/a/958742372_121681516', 'zh', 'CN', 'media', 2, 'Kiến trúc phần mềm/phần cứng gateway KNX-DALI'),
('sohu-knx-dali-lighting-application', '搜狐 — 浅谈智能照明系统KNX与DALI协议网关的应用', 'manual', 'https://www.sohu.com/a/734721093_121248877', 'zh', 'CN', 'media', 3, 'Ứng dụng gateway KNX-DALI trong chiếu sáng thông minh'),

-- Matter Smarthome — Article
('samsung-research-matter-1-6-release', 'Samsung Research — CSA Matter 1.6 Release', 'manual', 'https://research.samsung.com/blog/CSA-Matter-1-6-Release-Ambient-Sensing-More-Intuitive-Setup-Multi-Ecosystem-Experiences-and-Context-Driven-Control', 'en', 'global', 'manufacturer', 1, 'Chi tiết kỹ thuật chính thức Matter 1.6, nguồn uy tín cao'),
('matterhubs-best-matter-hubs-2026', 'Matterhubs — 10 Best Matter Supported Smart Hubs 2026', 'manual', 'https://blog.matterhubs.com/matter-hubs/', 'en', 'global', 'media', 2, 'Đối thủ content trực tiếp — dùng đối chiếu "Matter vs KNX"'),
('matterhubs-tapo-smart-plug-mini', 'Matterhubs — Tapo Smart Plug Mini (Matter)', 'manual', 'https://blog.matterhubs.com/tapo-smart-plug-mini/', 'en', 'global', 'media', 3, 'Review sản phẩm entry-level'),
('matterhubs-evehome-matter-devices', 'Matterhubs — Matter Compatible EveHome Devices', 'manual', 'https://blog.matterhubs.com/evehome-matter-devices/', 'en', 'global', 'media', 3, 'Review dòng thiết bị EveHome'),
('thinkrobotics-matter-protocol-guide-2025', 'ThinkRobotics — Matter Protocol Explained: Complete Guide 2025', 'manual', 'https://thinkrobotics.com/blogs/learn/matter-protocol-explained-for-smart-homes-complete-guide-2025', 'en', 'global', 'media', 2, 'Bài giải thích Matter toàn diện cho B2C'),

-- Matter Smarthome — Listing/Category feed (kind=html_list, B1 cần bóc tách danh sách link con)
('the-ambient-news-smart-home', 'The Ambient — News: Smart Home', 'html_list', 'https://www.the-ambient.com/news/smart-home/', 'en', 'UK', 'media', 1, 'Feed tin nhanh đa hãng (Google/Apple/Philips/Amazon)'),
('the-ambient-news-matter', 'The Ambient — News: Matter', 'html_list', 'https://www.the-ambient.com/news/matter/', 'en', 'UK', 'media', 1, 'Feed tin Matter chuyên biệt — giá trị nhất nhóm The Ambient'),
('the-ambient-reviews', 'The Ambient — Reviews', 'html_list', 'https://www.the-ambient.com/reviews/', 'en', 'UK', 'media', 1, 'Reviews thiết bị smart home đã kiểm chứng'),
('androidcentral-smart-home', 'Android Central — Smart Home', 'html_list', 'https://www.androidcentral.com/accessories/smart-home', 'en', 'global', 'media', 2, 'Thiên hệ sinh thái Google Home/Gemini'),
('engadget-smart-home-reviews', 'Engadget — Smart Home Reviews', 'html_list', 'https://www.engadget.com/category/smart-home-reviews/', 'en', 'global', 'media', 2, 'Độ phủ thấp (review thưa) — theo dõi thêm trước khi tăng tier'),
('staceyoniot-smart-home-tag', 'Stacey on IoT — Smart Home tag', 'html_list', 'https://staceyoniot.com/tag/smart-home/', 'en', 'global', 'media', 1, 'Phân tích IoT chuyên sâu, chất lượng kỹ thuật tốt'),
('home-assistant-blog', 'Home Assistant — Blog', 'html_list', 'https://www.home-assistant.io/blog/', 'en', 'global', 'community', 1, 'Nguồn chính thức open-source ecosystem, độ tin cậy cao'),
('csa-iot-newsroom', 'CSA IoT — Newsroom', 'html_list', 'https://csa-iot.org/newsroom/page/4/', 'en', 'global', 'standard_body', 1, 'Nguồn chính thức uy tín nhất cho tin chuẩn Matter'),
('matter-smarthome-de-practice', 'Matter Smarthome DE — Practice', 'html_list', 'https://matter-smarthome.de/en/practice/', 'en', 'DE', 'media', 2, 'Hướng dẫn thực hành Matter (tác giả Frank-Oliver Grün)'),
('matter-smarthome-de-development', 'Matter Smarthome DE — Development', 'html_list', 'https://matter-smarthome.de/en/development/', 'en', 'DE', 'media', 2, 'Roadmap Matter, gồm bài KNX IoT + Matter integration. Gộp page/3,4,5 vào đây — chỉ theo dõi 1 feed'),
('smartthings-blog-matter', 'SmartThings Blog — Category: Matter', 'html_list', 'https://blog.smartthings.com/category/matter/', 'en', 'global', 'manufacturer', 2, 'Nguồn chính thức Samsung, thiên marketing hệ sinh thái'),
('aqara-blog', 'Aqara — Blog', 'html_list', 'https://www.aqara.com/en/blog/', 'en', 'global', 'manufacturer', 1, 'Case study quy mô lớn (KAFD 10.000+ devices) hữu ích B2B lẫn B2C')

ON CONFLICT (url) DO NOTHING;
