#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 -m uvicorn app:app --host 0.0.0.0 --port 8800
