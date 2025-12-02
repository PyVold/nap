#!/bin/bash
# Database Migration Runner
# Runs SQL migration files against the NAP database

set -e  # Exit on error

echo "=============================================================================="
echo "NAP Database Migration Runner"
echo "=============================================================================="
echo ""

# Check if we can use docker compose or docker-compose
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DC="docker compose"
else
    echo "ERROR: docker-compose not found"
    echo "Please install Docker Compose first"
    exit 1
fi

# Database connection details
DB_USER="nap_user"
DB_NAME="nap_db"
MIGRATION_FILE="${1:-migrations/001_add_system_config_table.sql}"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "ERROR: Migration file not found: $MIGRATION_FILE"
    echo ""
    echo "Usage: ./run_migration.sh [migration_file]"
    echo "Example: ./run_migration.sh migrations/001_add_system_config_table.sql"
    exit 1
fi

echo "Migration file: $MIGRATION_FILE"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Check if database container is running
if ! $DC ps database | grep -q "Up"; then
    echo "ERROR: Database container is not running"
    echo "Please start containers first: $DC up -d"
    exit 1
fi

echo "Running migration..."
echo ""

# Run the migration
$DC exec -T database psql -U "$DB_USER" -d "$DB_NAME" -f - < "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "=============================================================================="
    echo "✅ Migration completed successfully!"
    echo "=============================================================================="
else
    echo ""
    echo "=============================================================================="
    echo "❌ Migration failed!"
    echo "=============================================================================="
    exit 1
fi
