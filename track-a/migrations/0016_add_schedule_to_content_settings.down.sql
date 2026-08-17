ALTER TABLE news.content_settings
  DROP COLUMN IF EXISTS schedule_enabled,
  DROP COLUMN IF EXISTS schedule_hour,
  DROP COLUMN IF EXISTS schedule_minute;
