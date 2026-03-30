#!/usr/bin/env bash
# K-plane only: full gate run on a host with AF_UNIX / SOCK_STREAM socketpair (Linux or macOS).
# Run from repo root: bash scripts/run_linux_af_unix_gates.sh
# Optional: LOG=linux_af_unix_gate_transcript.txt bash scripts/run_linux_af_unix_gates.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -n "${LOG:-}" ]]; then
  exec > >(tee -a "$LOG") 2>&1
fi

echo "================================================================================"
echo "K-plane AF_UNIX / UDS gate — same-context evidence"
echo "================================================================================"
echo "=== PLATFORM ==="
uname -a || true
echo "=== PYTHON (uv) ==="
uv run python -V
echo "=== AF_UNIX probe ==="
uv run python -c "import socket; print('AF_UNIX:', getattr(socket, 'AF_UNIX', None)); a,b=socket.socketpair(getattr(socket,'AF_UNIX'), socket.SOCK_STREAM); print('socketpair: ok'); a.close(); b.close()"
echo "=== GIT COMMIT ==="
git rev-parse HEAD
echo "=== RUFF ==="
uv run ruff check .
echo "=== MYPY ==="
uv run mypy src tests
echo "=== PYTEST (full, verbose) ==="
uv run pytest tests/ -v --tb=short
echo "================================================================================"
echo "K-plane AF_UNIX / UDS gate — end"
echo "================================================================================"
