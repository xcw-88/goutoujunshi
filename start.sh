#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

command -v python3 >/dev/null || { echo "Python 3.12+ is required." >&2; exit 1; }
command -v node >/dev/null || { echo "Node.js 20.9+ is required." >&2; exit 1; }
[[ -x "$BACKEND_PYTHON" ]] || { echo "Run: cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'" >&2; exit 1; }
[[ -d "$ROOT_DIR/frontend/node_modules" ]] || { echo "Run: cd frontend && npm install" >&2; exit 1; }

mkdir -p "$ROOT_DIR/data/logs" "$ROOT_DIR/data/uploads" "$ROOT_DIR/data/exports"

(cd "$ROOT_DIR/backend" && "$BACKEND_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) >"$ROOT_DIR/data/logs/backend.out.log" 2>"$ROOT_DIR/data/logs/backend.err.log" &
BACKEND_PID=$!
(cd "$ROOT_DIR/frontend" && npm run dev) >"$ROOT_DIR/data/logs/frontend.out.log" 2>"$ROOT_DIR/data/logs/frontend.err.log" &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

printf '\nGoutoujunshi Web\n\nBackend:  http://127.0.0.1:8000\nFrontend: http://127.0.0.1:3000\nAPI Docs: http://127.0.0.1:8000/docs\n\nPress Ctrl+C to stop both services.\n'
wait -n "$BACKEND_PID" "$FRONTEND_PID"

