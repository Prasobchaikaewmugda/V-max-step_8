#!/usr/bin/env bash
# Canonical Linux/POSIX gate transcript for Chat 3 hostile-review packets.
# Run from repository root after: git checkout <exact-anchor-commit>
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "================================================================================"
echo "K-plane gates — Chat 3 unified packet (Linux/POSIX)"
echo "================================================================================"
echo "=== PLATFORM ==="
uname -a
echo "=== GIT ==="
echo "PWD: $ROOT"
echo "COMMIT (full): $(git rev-parse HEAD)"
echo "=== PYTHON (uv) ==="
uv run python -V
echo ""
echo "Command: uv run ruff check ."
echo "--- stdout ---"
uv run ruff check .
echo ""
echo "Command: uv run mypy src tests"
echo "--- stdout ---"
uv run mypy src tests
echo ""
echo "Command: uv run pytest tests/ -v --tb=short"
echo "--- stdout ---"
uv run pytest tests/ -v --tb=short
