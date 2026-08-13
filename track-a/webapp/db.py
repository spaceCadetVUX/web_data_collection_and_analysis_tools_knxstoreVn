"""Kết nối Postgres dev — đọc credential từ track-a/src/.env (không commit)."""
import os
from pathlib import Path

import psycopg2
import psycopg2.extras

ENV_PATH = Path(__file__).resolve().parent.parent / "src" / ".env"


def _load_env():
    values = {}
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


_env = _load_env()

DB_URL = (
    f"postgresql://{_env['POSTGRES_USER']}:{_env['POSTGRES_PASSWORD']}"
    f"@localhost:{_env['POSTGRES_PORT']}/{_env['POSTGRES_DB']}"
)


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
