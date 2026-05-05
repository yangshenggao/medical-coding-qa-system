#!/bin/sh
set -eu

mkdir -p "${CHROMA_PERSIST_DIR:-/app/data/chroma}" "${UPLOAD_FOLDER:-/app/data/uploads}"

python - <<'PY'
import os
import socket
import sys
import time

host = os.environ.get('MYSQL_HOST', 'mysql')
port = int(os.environ.get('MYSQL_PORT', '3306'))
deadline = time.time() + 120

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            sys.exit(0)
    except OSError:
        time.sleep(2)

print(f'MySQL not ready: {host}:{port}', file=sys.stderr)
sys.exit(1)
PY

exec python app.py
