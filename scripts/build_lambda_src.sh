#!/usr/bin/env bash
# Builds a lean Lambda source dir (.lambda/) - deterministic mode, no LLM libs.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf .lambda && mkdir -p .lambda
cp -r app.py alerts_handler.py saanssafe static .lambda/
find .lambda -name __pycache__ -prune -exec rm -rf {} +
printf 'fastapi\nmangum\n' > .lambda/requirements.txt
