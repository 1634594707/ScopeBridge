#!/bin/sh
# Migrate, then serve. The database is a separate container, so its first
# seconds after start are spent not accepting connections; retrying is the
# wait, and running out of retries is a failure, not a reason to serve anyway.
set -eu

attempt=0
until alembic upgrade head; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "database did not accept migrations after 30 attempts" >&2
        exit 1
    fi
    echo "waiting for the database (attempt ${attempt}/30)" >&2
    sleep 2
done

# The demo accounts and rule version are seeded only when asked for, so the same
# image can be pointed at a database that already has real data.
if [ "${SEED_DEMO_DATA:-0}" = "1" ]; then
    python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
