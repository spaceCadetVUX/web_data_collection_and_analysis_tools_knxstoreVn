ALTER TABLE news.content_settings
  DROP COLUMN IF EXISTS schedule_frequency,
  DROP COLUMN IF EXISTS schedule_weekday;
