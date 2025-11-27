# Database Migrations

⚠️ **IMPORTANT:** The existing migration scripts in this directory are designed for SQLite and **will not work** with PostgreSQL (used in Docker/production).

## Status

The current migration scripts use SQLite-specific syntax and `sqlite3` module:
- `add_device_backoff_tracking.py`
- `add_discovery_group_excluded_ips.py`
- `add_hardware_inventory.py`
- `add_ssh_health_check.py`

## Recommended Solution

Migrate to **Alembic** for proper database migration management that supports multiple databases.

### Quick Start with Alembic

1. **Install Alembic:**
   ```bash
   pip install alembic
   ```

2. **Initialize Alembic:**
   ```bash
   cd /workspace
   alembic init alembic
   ```

3. **Configure Alembic:**
   Edit `alembic.ini` and set:
   ```ini
   sqlalchemy.url = postgresql://nap_user:nap_password@localhost:5432/nap_db
   ```

4. **Import Base models:**
   Edit `alembic/env.py` and add:
   ```python
   from shared.database import Base
   # Import all models
   import services.device-service.app.db_models
   target_metadata = Base.metadata
   ```

5. **Generate migrations:**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

6. **Apply migrations:**
   ```bash
   alembic upgrade head
   ```

## Alternative: Manual Schema Creation

If you prefer not to use Alembic, the database schema is automatically created by SQLAlchemy when services start up, using `Base.metadata.create_all()` in `shared/database.py`.

This is suitable for development but not recommended for production.

## For Production

1. **Use Alembic** for proper migration tracking
2. **Version control** all migration files
3. **Test migrations** on a staging database first
4. **Backup database** before running migrations
5. **Run migrations** during deployment:
   ```bash
   docker-compose exec device-service alembic upgrade head
   ```

## Migration from SQLite to PostgreSQL

If you have existing SQLite data:

1. **Export data:**
   ```bash
   sqlite3 network_audit.db .dump > backup.sql
   ```

2. **Convert to PostgreSQL format:**
   ```bash
   # Remove SQLite-specific syntax
   sed -i 's/AUTOINCREMENT//' backup.sql
   ```

3. **Import to PostgreSQL:**
   ```bash
   psql -U nap_user -d nap_db -f backup.sql
   ```

## See Also

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Migrations Guide](https://docs.sqlalchemy.org/en/20/core/metadata.html)
