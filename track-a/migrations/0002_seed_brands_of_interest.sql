-- Seed registry.brands_of_interest từ danh sách brand KNXStore cung cấp (2026-08-13).
-- Nguồn thô: track-a/data/knxstore-brands-raw.txt (75 dòng — bạn ghi nhãn "80 brands",
-- lệch 5, cần kiểm tra lại nguồn gốc danh sách).
--
-- CHƯA CHẠY trên Postgres thật — chờ credential (xem track-a/README.md mục 5, câu #5).
-- Cú pháp đã test được trên Postgres tạm (không phải suy đoán).
--
-- Alias trong file này đã VERIFY bằng grep trực tiếp trên dữ liệu KNX/Matter thật đã
-- crawl (track-a/data/knx_devices_baseline.csv, matter_devices_baseline.csv) — không
-- phải suy diễn từ thuật toán fuzzy match (fuzzy match ban đầu có nhiều nhiễu, ví dụ gợi ý
-- sai "Lutron" ~ "Lunatone", đã loại bỏ).

-- Loại khỏi seed — rõ ràng KHÔNG PHẢI tên nhà sản xuất, không phải suy đoán:
--   'Khác'                    -> nghĩa "Other/Miscellaneous" trong danh mục KNXStore
--   'Casambi Enocean Switch'  -> tên loại sản phẩm, không phải tên hãng

INSERT INTO registry.brands_of_interest (brand) VALUES
  ('HUGO MULLER'),
  ('ABB'),
  ('Enertex Bayern GmbH'),
  ('Core'),
  ('Protopixel'),
  ('Apple'),
  ('JINK'),
  ('Rayrun'),
  ('AIMOTION'),
  ('Maintronic'),
  ('Panasonic'),
  ('Tailwind'),
  ('CBC Computar'),
  ('RESI'),
  ('Ekinex'),
  ('URC'),
  ('GVS'),
  ('Homey'),
  ('Aqara'),
  ('Eve'),
  ('Micro Air'),
  ('Elsner'),
  ('Steinel'),
  ('Remotec'),
  ('OEM'),
  ('Airzone'),
  ('Versaan'),
  ('UITIOT'),
  ('LAPP'),
  ('Vera'),
  ('ThinKNX'),
  ('Kelvin and Lux'),
  ('Systemline E50'),
  ('Bruns'),
  ('LTECH'),
  ('Tado'),
  ('Maximum Security'),
  ('Helvar'),
  ('Vlinca'),
  ('Lite-Puter'),
  ('Legrand'),
  ('Olfer'),
  ('Scemtec'),
  ('DALCNET'),
  ('Danlers'),
  ('DMX Engineering'),
  ('Bticino'),
  ('Tridonic'),
  ('Azoula'),
  ('Sunricher'),
  ('Atios'),
  ('Intesis'),
  ('Kaiterra'),
  ('Daikin'),
  ('EBELONG'),
  ('Cool Automation'),
  ('Siqitech'),
  ('Moorgen'),
  ('CP Electronics'),
  ('Trivum'),
  ('Philips Hue'),
  ('MDT'),
  ('Kanonbus'),
  ('Lutron'),
  ('THIEA'),
  ('Satel'),
  ('Vadsbo'),
  ('Weinzierl'),
  ('Lunatone'),
  ('Casambi'),
  ('Carus'),
  ('IR-TEC'),
  ('GOAP')
ON CONFLICT (brand) DO NOTHING;

-- Alias đã verify bằng grep trực tiếp trên dữ liệu crawl thật (không suy đoán)
UPDATE registry.brands_of_interest SET aliases = ARRAY['Hugo', 'Hugo Müller GmbH & Co KG'] WHERE brand = 'HUGO MULLER';
UPDATE registry.brands_of_interest SET aliases = ARRAY['ABB AG (Busch - Jaeger)', 'ABB AG (Stotz - Kontakt)', 'ABB SpA-SACE Division', 'ABB Xiamen Smart Technology Co., Ltd.'] WHERE brand = 'ABB';
UPDATE registry.brands_of_interest SET aliases = ARRAY['LEGRAND Appareillage électrique', 'Legrand Group'] WHERE brand = 'Legrand';
UPDATE registry.brands_of_interest SET aliases = ARRAY['Weinzierl Engineering GmbH'] WHERE brand = 'Weinzierl';
UPDATE registry.brands_of_interest SET aliases = ARRAY['MDT technologies'] WHERE brand = 'MDT';
UPDATE registry.brands_of_interest SET aliases = ARRAY['Satel sp. z o.o.'] WHERE brand = 'Satel';
UPDATE registry.brands_of_interest SET aliases = ARRAY['Elsner Elektronik GmbH'] WHERE brand = 'Elsner';
UPDATE registry.brands_of_interest SET aliases = ARRAY['Ekinex S.p.A.'] WHERE brand = 'Ekinex';
UPDATE registry.brands_of_interest SET aliases = ARRAY['CoolAutomation'] WHERE brand = 'Cool Automation';
UPDATE registry.brands_of_interest SET aliases = ARRAY['STEINEL professional'] WHERE brand = 'Steinel';
UPDATE registry.brands_of_interest SET aliases = ARRAY['AIRZONE – ALTRA'] WHERE brand = 'Airzone';
UPDATE registry.brands_of_interest SET aliases = ARRAY['Kanontec - KanonBUS'] WHERE brand = 'Kanonbus';
-- Đã xác nhận (2026-08-13): 'Kanonbus' là tên hãng thật, không phải dòng sản phẩm của hãng
-- khác — giữ nguyên trong seed, alias 'Kanontec - KanonBUS' áp dụng bình thường.

-- Cần Tùng xác nhận trước khi tin — KHÔNG tự quyết định, chỉ ghi alias khả nghi:
-- 'RESI' <-> 'Resideo' trong dữ liệu Matter — không chắc cùng công ty, chỉ là gợi ý tên gần
--   giống, chưa UPDATE alias.
-- 'Systemline E50' — nghi là dòng sản phẩm của hãng "Trivum" (đã có sẵn trong list riêng),
--   không phải tên hãng độc lập. Cần xác nhận có nên gộp làm alias của Trivum không.
-- 'OEM', 'Maximum Security' — tên nghe chung chung, không chắc là tên hãng cụ thể.
