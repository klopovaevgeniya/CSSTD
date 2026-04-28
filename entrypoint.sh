#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${COLLECTSTATIC_ON_START:-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

APP_CMD=${APP_CMD:-gunicorn csstd.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120}

exec sh -c "$APP_CMD"
