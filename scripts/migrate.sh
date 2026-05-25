#!/bin/bash

set -e

HOST=${DB_HOST:-localhost}
PORT=${DB_PORT:-5432}
DB=${DB_NAME:-rodent_pipeline}
USER=${DB_USER:-postgres}

echo "Running migrations..."

psql -h $HOST -p $PORT -d $DB -U $USER \
    -f migrations/001_create_inspections.sql \
    -f migrations/002_create_borough_rodent_summary.sql \
    -f migrations/003_create_monthly_inspection_trends.sql \
    -f migrations/004_create_zipcode_hotspots.sql

echo "Migrations complete"