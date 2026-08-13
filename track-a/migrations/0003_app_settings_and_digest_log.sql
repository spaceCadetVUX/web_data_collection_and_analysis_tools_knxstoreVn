-- Thêm bảng cho webapp Track A (thay n8n) — xem track-a/webapp/.
-- registry.app_settings: 1 dòng duy nhất, lưu lịch weekly để Settings page sửa được mà
-- không cần đụng launchd/plist. registry.digest_log: lịch sử mỗi lần gửi digest, cho trang Logs.

CREATE TABLE registry.app_settings (
  id               smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  schedule_weekday smallint NOT NULL DEFAULT 0 CHECK (schedule_weekday BETWEEN 0 AND 6),
  -- 0 = Monday .. 6 = Sunday (quy ước APScheduler cron 'day_of_week', không phải cron Unix)
  schedule_hour    smallint NOT NULL DEFAULT 8 CHECK (schedule_hour BETWEEN 0 AND 23),
  schedule_minute  smallint NOT NULL DEFAULT 0 CHECK (schedule_minute BETWEEN 0 AND 59),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

INSERT INTO registry.app_settings (id, schedule_weekday, schedule_hour, schedule_minute)
VALUES (1, 0, 8, 0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE registry.digest_log (
  id            bigserial PRIMARY KEY,
  run_at        timestamptz NOT NULL DEFAULT now(),
  trigger_type  text NOT NULL CHECK (trigger_type IN ('scheduled', 'manual')),
  device_count  int,
  message       text,
  send_status   text CHECK (send_status IN ('ok', 'failed', 'skipped_no_credential')),
  error         text,
  duration_ms   int
);
CREATE INDEX ON registry.digest_log (run_at DESC);
