-- Track B: thêm lựa chọn cadence hàng tuần bên cạnh hàng ngày (0016). Mặc định vẫn 'daily' —
-- không đổi hành vi của lịch đã cấu hình trước đó. schedule_weekday dùng chung quy ước
-- APScheduler day_of_week 0=Monday như registry.app_settings (xem 0003), chỉ có ý nghĩa khi
-- schedule_frequency='weekly'.

ALTER TABLE news.content_settings
  ADD COLUMN schedule_frequency text NOT NULL DEFAULT 'daily'
    CHECK (schedule_frequency IN ('daily', 'weekly')),
  ADD COLUMN schedule_weekday smallint DEFAULT 0 CHECK (schedule_weekday BETWEEN 0 AND 6);
