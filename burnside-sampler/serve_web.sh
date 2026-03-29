#!/bin/sh
set -eu

PORT="${1:-8000}"
python -m http.server "$PORT"
