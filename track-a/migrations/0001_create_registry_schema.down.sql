-- Rollback cho 0001_create_registry_schema.sql
-- Chạy bằng: psql "$DATABASE_URL" -f 0001_create_registry_schema.down.sql

DROP SCHEMA IF EXISTS registry CASCADE;
