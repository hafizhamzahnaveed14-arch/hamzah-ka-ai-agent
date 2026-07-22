#!/bin/sh
# Railway sets $PORT — bind API to it.
set -e
exec uvicorn alphaquant_api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --app-dir api
