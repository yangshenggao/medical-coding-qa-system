#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
MYSQL_PID_FILE="$RUNTIME_DIR/mysql.pid"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
MYSQL_SOCKET="${MYSQL_SOCKET:-/tmp/medical_coding_mysql.sock}"
MYSQL_BIN="${MYSQL_BIN:-mysql}"
MYSQLADMIN_BIN="${MYSQLADMIN_BIN:-mysqladmin}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3308}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
BACKEND_PORT="${BACKEND_PORT:-5002}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

print_step() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

mysql_admin_ping() {
  MYSQL_PWD="$MYSQL_PASSWORD" "$MYSQLADMIN_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" ping >/dev/null 2>&1
}

stop_by_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 1
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    print_step "Stopping ${name} (pid ${pid})"
    kill "$pid" >/dev/null 2>&1 || true
    for _ in $(seq 1 20); do
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi

  rm -f "$pid_file"
  return 0
}

stop_by_port() {
  local name="$1"
  local port="$2"
  local pids

  pids="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 1
  fi

  print_step "Stopping ${name} on port ${port}"
  for pid in $pids; do
    kill "$pid" >/dev/null 2>&1 || true
  done

  sleep 1

  pids="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    for pid in $pids; do
      kill -9 "$pid" >/dev/null 2>&1 || true
    done
  fi

  return 0
}

stop_frontend() {
  stop_by_pid_file "frontend" "$FRONTEND_PID_FILE" || stop_by_port "frontend" "$FRONTEND_PORT" || true
}

stop_backend() {
  stop_by_pid_file "backend" "$BACKEND_PID_FILE" || stop_by_port "backend" "$BACKEND_PORT" || true
}

stop_mysql() {
  if mysql_admin_ping; then
    print_step "Stopping MySQL on ${MYSQL_HOST}:${MYSQL_PORT}"
    MYSQL_PWD="$MYSQL_PASSWORD" "$MYSQLADMIN_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" shutdown >/dev/null 2>&1 || true
    sleep 1
  fi

  stop_by_pid_file "mysql" "$MYSQL_PID_FILE" || stop_by_port "mysql" "$MYSQL_PORT" || true
  rm -f "$MYSQL_SOCKET"
}

stop_frontend
stop_backend
stop_mysql

print_step "Project services stopped"
