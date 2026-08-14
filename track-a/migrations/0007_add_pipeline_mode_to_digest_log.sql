-- Track riêng full pipeline (KNX+Matter, ~15-20 phút) vs incremental pipeline (chỉ KNX,
-- chỉ thiết bị mới, vài giây tới vài chục giây) trong registry.digest_log — không lấn vào
-- trigger_type (đã có CHECK riêng cho scheduled/manual, xem 0003_app_settings_and_digest_log.sql).

ALTER TABLE registry.digest_log
  ADD COLUMN pipeline_mode text NOT NULL DEFAULT 'full' CHECK (pipeline_mode IN ('full', 'incremental'));
