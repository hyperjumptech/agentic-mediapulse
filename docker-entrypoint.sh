#!/usr/bin/env sh
set -e

# Apply pending migrations on startup, unless disabled (RUN_MIGRATIONS=0) or no database is configured.
# Set RUN_MIGRATIONS=0 and pass `alembic upgrade head` as the command to run migrations as a standalone job.
if [ "${RUN_MIGRATIONS:-1}" != "0" ] && [ -n "$DATABASE_URL" ]; then
    echo "Applying database migrations (alembic upgrade head)..."
    alembic upgrade head
fi

exec "$@"
