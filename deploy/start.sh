#!/bin/sh
# One container: Streamlit dashboard + FastAPI behind one public port, sharing one SQLite file.
set -e
export CITIZEN_DB="${CITIZEN_DB:-/app/storage/citizens.sqlite3}"
mkdir -p "$(dirname "$CITIZEN_DB")"
if [ -z "$CITIZEN_API_KEY" ]; then
  CITIZEN_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  export CITIZEN_API_KEY
fi
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log &
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 \
  --server.headless true --browser.gatherUsageStats false &
exec caddy run --config /app/deploy/Caddyfile --adapter caddyfile
