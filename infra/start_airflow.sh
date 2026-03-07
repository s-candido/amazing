#!/usr/bin/env bash

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! pg_isready -h postgresql -p 5432 -U mlflow; do
  sleep 1
done

echo "Database is ready!"

# Reset the database (only on first run or when needed)
if [ ! -f /tmp/db_initialized ]; then
  echo "Initializing the Airflow database..."
  airflow db reset --yes
  touch /tmp/db_initialized
fi

echo "Creating admin user..."
airflow users create \
    --username admin \
    --firstname FIRST_NAME \
    --lastname LAST_NAME \
    --role Admin \
    --email admin@example.com \
    --password admin 2>/dev/null || true

echo "Starting $1..."
exec airflow "$1"