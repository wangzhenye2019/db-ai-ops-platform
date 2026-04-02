#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Backend: compileall"
python3 -m compileall backend

echo "Backend: pytest"
export PYTHONPATH="backend"
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
pytest -q backend/tests

echo "Frontend: build"
cd frontend
npm ci
npm run build
