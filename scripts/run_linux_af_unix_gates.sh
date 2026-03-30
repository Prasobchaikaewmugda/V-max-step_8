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
uv run python - <<'PY'
import socket
import sys

u = getattr(socket, "AF_UNIX", None)
print("AF_UNIX:", u)
if u is None:
    sys.stderr.write(
        "ERROR: AF_UNIX not available on this Python interpreter. "
        "Run this script on Linux or macOS with AF_UNIX socketpair support.\n"
    )
    raise SystemExit(1)
a, b = socket.socketpair(u, socket.SOCK_STREAM)
print("socketpair: ok")
a.close()
b.close()
PY
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
