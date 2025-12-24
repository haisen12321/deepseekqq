#!/usr/bin/env sh
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)

if [ -f "${PROJECT_DIR}/.env" ]; then
  echo "Using ${PROJECT_DIR}/.env"
else
  echo "Please create ${PROJECT_DIR}/.env from .env.example"
  exit 1
fi

python -m app.server
