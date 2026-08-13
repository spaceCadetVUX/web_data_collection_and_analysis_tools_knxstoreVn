-- Rollback cho 0003_app_settings_and_digest_log.sql
-- Chạy bằng: psql "$DATABASE_URL" -f 0003_app_settings_and_digest_log.down.sql

DROP TABLE IF EXISTS registry.digest_log;
DROP TABLE IF EXISTS registry.app_settings;
