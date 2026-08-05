#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be provided through Secret Manager}"
: "${JWT_SECRET:?JWT_SECRET must be provided through Secret Manager}"

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
