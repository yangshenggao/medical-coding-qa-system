#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$ROOT_DIR/项目源码/server"
CLIENT_DIR="$ROOT_DIR/项目源码/client"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"
MYSQL_DATA_DIR="$RUNTIME_DIR/mysql-data"
MYSQL_SOCKET="${MYSQL_SOCKET:-/tmp/medical_coding_mysql.sock}"
MYSQL_PID_FILE="$RUNTIME_DIR/mysql.pid"
MYSQL_BASE="${MYSQL_BASE:-/usr/local/mysql}"
MYSQLD="$MYSQL_BASE/bin/mysqld"
MYSQL_BIN="${MYSQL_BIN:-mysql}"
MYSQLADMIN_BIN="${MYSQLADMIN_BIN:-mysqladmin}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
SERVER_PYTHON="$SERVER_DIR/.venv312/bin/python"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-5002}"
MYSQL_PORT="${MYSQL_PORT:-3308}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-db_medical_coding}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
SQL_FILE="$SERVER_DIR/sql/init.sql"
UPLOAD_DIR="$SERVER_DIR/uploads"
CHROMA_DB_FILE="$SERVER_DIR/chroma_medical/chroma.sqlite3"
MEDICAL_DICT_DIR="${MEDICAL_DICT_DIR:-$ROOT_DIR/知识库文件}"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
OLLAMA_LOG="$LOG_DIR/ollama.log"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"

print_step() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

wait_for_http() {
  local url="$1"
  local retries="${2:-30}"
  local delay="${3:-1}"
  for _ in $(seq 1 "$retries"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

wait_for_backend() {
  local url="$1"
  local retries="${2:-30}"
  local delay="${3:-1}"
  local code
  for _ in $(seq 1 "$retries"); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" || true)"
    if [[ "$code" == "200" || "$code" == "401" ]]; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

wait_for_mysql() {
  local retries="${1:-30}"
  local delay="${2:-1}"
  for _ in $(seq 1 "$retries"); do
    if mysql_admin_ping; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

mysql_exec() {
  MYSQL_PWD="$MYSQL_PASSWORD" "$MYSQL_BIN" -h"$MYSQL_HOST" -u"$MYSQL_USER" -P"$MYSQL_PORT" "$@"
}

mysql_admin_ping() {
  MYSQL_PWD="$MYSQL_PASSWORD" "$MYSQLADMIN_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" ping >/dev/null 2>&1
}

start_ollama_if_needed() {
  if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    print_step "Ollama already running"
    return
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama is not installed or not in PATH. Please start Ollama first."
    exit 1
  fi

  print_step "Starting Ollama"
  nohup ollama serve >"$OLLAMA_LOG" 2>&1 &

  if ! wait_for_http "$OLLAMA_URL/api/tags" 20 1; then
    echo "Failed to start Ollama. Check $OLLAMA_LOG"
    exit 1
  fi
}

ensure_backend_venv() {
  if [[ ! -x "$SERVER_PYTHON" ]]; then
    print_step "Creating backend virtual environment with $PYTHON_BIN"
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
      echo "Missing $PYTHON_BIN. Please install Python 3.12 first."
      exit 1
    }
    "$PYTHON_BIN" -m venv "$SERVER_DIR/.venv312"
    "$SERVER_DIR/.venv312/bin/python" -m pip install --upgrade pip setuptools wheel
    "$SERVER_DIR/.venv312/bin/pip" install -r "$SERVER_DIR/requirements.txt"
  fi
}

ensure_frontend_deps() {
  if [[ ! -d "$CLIENT_DIR/node_modules" ]]; then
    print_step "Installing frontend dependencies"
    (cd "$CLIENT_DIR" && npm install)
  fi
}

start_mysql_if_needed() {
  if mysql_admin_ping; then
    print_step "MySQL already running on $MYSQL_HOST:$MYSQL_PORT"
    return
  fi

  if [[ ! -x "$MYSQLD" ]]; then
    echo "MySQL server binary not found at $MYSQLD"
    exit 1
  fi

  if [[ ! -d "$MYSQL_DATA_DIR/mysql" ]]; then
    print_step "Initializing MySQL data directory"
    mkdir -p "$MYSQL_DATA_DIR"
    "$MYSQLD" \
      --initialize-insecure \
      --basedir="$MYSQL_BASE" \
      --datadir="$MYSQL_DATA_DIR"
  fi

  print_step "Starting MySQL on port $MYSQL_PORT"
  "$MYSQLD" \
    --daemonize \
    --basedir="$MYSQL_BASE" \
    --datadir="$MYSQL_DATA_DIR" \
    --port="$MYSQL_PORT" \
    --bind-address="$MYSQL_HOST" \
    --mysqlx=0 \
    --socket="$MYSQL_SOCKET" \
    --pid-file="$MYSQL_PID_FILE"

  if ! wait_for_mysql 30 1; then
    echo "Failed to start MySQL on $MYSQL_HOST:$MYSQL_PORT"
    exit 1
  fi
}

seed_and_fix_database() {
  local db_exists
  db_exists="$(mysql_exec -Nse "SHOW DATABASES LIKE '$MYSQL_DATABASE';" || true)"

  if [[ -z "$db_exists" ]]; then
    print_step "Importing database seed"
    mysql_exec < "$SQL_FILE"
  fi

  print_step "Applying local database fixes"
  mysql_exec <<SQL
USE \`${MYSQL_DATABASE}\`;
UPDATE t_document
SET file_path = CONCAT('${UPLOAD_DIR}/', SUBSTRING_INDEX(REPLACE(file_path, '\\\\', '/'), '/', -1));
SQL
}

reindex_if_needed() {
  if [[ -f "$CHROMA_DB_FILE" && "${FORCE_REINDEX:-0}" != "1" ]]; then
    print_step "Using existing Chroma index"
    return
  fi

  print_step "Rebuilding Chroma index"
  rm -rf "$SERVER_DIR/chroma_medical"
  mkdir -p "$SERVER_DIR/chroma_medical"

  (
    cd "$SERVER_DIR"
    MYSQL_HOST="$MYSQL_HOST" \
    MYSQL_PORT="$MYSQL_PORT" \
    MYSQL_USER="$MYSQL_USER" \
    MYSQL_PASSWORD="$MYSQL_PASSWORD" \
    MYSQL_DATABASE="$MYSQL_DATABASE" \
    CHROMA_PERSIST_DIR="$SERVER_DIR/chroma_medical" \
    MEDICAL_DICT_DIR="$MEDICAL_DICT_DIR" \
    "$SERVER_PYTHON" - <<'PY'
from app import create_app
from models import db
from models.document import Document
from models.knowledge_base import KnowledgeBase
from services.vector_service import VectorService
import os

app = create_app()
with app.app_context():
    vector_service = VectorService()
    docs = Document.query.order_by(Document.id).all()
    for doc in docs:
        if not os.path.exists(doc.file_path):
            doc.status = 'failed'
            db.session.commit()
            continue
        chunk_count = vector_service.process_document(doc.id, doc.file_path, doc.file_type, doc.kb_id)
        doc.chunk_count = chunk_count
        doc.status = 'vectorized'
        db.session.commit()

    for kb in KnowledgeBase.query.order_by(KnowledgeBase.id).all():
        kb.doc_count = Document.query.filter_by(kb_id=kb.id, status='vectorized').count()
    db.session.commit()
PY
  )
}

start_backend() {
  if wait_for_backend "http://127.0.0.1:${BACKEND_PORT}/api/auth/info" 1 0; then
    print_step "Backend already running on port $BACKEND_PORT"
    return
  fi

  print_step "Starting backend on port $BACKEND_PORT"
  (
    cd "$SERVER_DIR"
    nohup env \
      FLASK_HOST=0.0.0.0 \
      FLASK_PORT="$BACKEND_PORT" \
      FLASK_DEBUG=false \
      MYSQL_HOST="$MYSQL_HOST" \
      MYSQL_PORT="$MYSQL_PORT" \
      MYSQL_USER="$MYSQL_USER" \
      MYSQL_PASSWORD="$MYSQL_PASSWORD" \
      MYSQL_DATABASE="$MYSQL_DATABASE" \
      CHROMA_PERSIST_DIR="$SERVER_DIR/chroma_medical" \
      MEDICAL_DICT_DIR="$MEDICAL_DICT_DIR" \
      "$SERVER_PYTHON" app.py >"$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
  )

  if ! wait_for_backend "http://127.0.0.1:${BACKEND_PORT}/api/auth/info" 30 1; then
    echo "Failed to start backend. Check $BACKEND_LOG"
    exit 1
  fi
}

start_frontend() {
  if curl -sf "http://127.0.0.1:${FRONTEND_PORT}" >/dev/null 2>&1; then
    print_step "Frontend already running on port $FRONTEND_PORT"
    return
  fi

  print_step "Starting frontend on port $FRONTEND_PORT"
  (
    cd "$CLIENT_DIR"
    nohup npm run dev -- --host 127.0.0.1 >"$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )

  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 30 1; then
    echo "Failed to start frontend. Check $FRONTEND_LOG"
    exit 1
  fi
}

print_step "Preparing runtime"
ensure_backend_venv
ensure_frontend_deps
start_ollama_if_needed
start_mysql_if_needed
seed_and_fix_database
reindex_if_needed
start_backend
start_frontend

cat <<EOF

Project is ready.
Frontend: http://127.0.0.1:${FRONTEND_PORT}
Backend:  http://127.0.0.1:${BACKEND_PORT}
MySQL:    ${MYSQL_HOST}:${MYSQL_PORT}
Dict dir: ${MEDICAL_DICT_DIR}

Admin login:
  username: admin
  password: 123456

Logs:
  backend:  ${BACKEND_LOG}
  frontend: ${FRONTEND_LOG}
  ollama:   ${OLLAMA_LOG}
EOF
