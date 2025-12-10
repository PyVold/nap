from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from shared.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url or "sqlite:///./network_audit.db"

# Configure connection pool settings for production
pool_config = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite-specific settings
    pool_config = {"check_same_thread": False}
else:
    # PostgreSQL/Production settings
    pool_config = {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,              # Maximum number of connections to keep open
    max_overflow=20,           # Maximum overflow connections beyond pool_size
    pool_pre_ping=True,        # Verify connections before using them
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo=False,                # Set to True for SQL debugging
    connect_args=pool_config
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and indexes, skipping if they already exist"""
    from sqlalchemy.exc import ProgrammingError

    # Import all models to ensure they're registered with Base
    # Services have their own db_models.py that should be used
    try:
        import db_models  # Service-local db_models
    except ImportError:
        import shared.db_models  # Fallback to shared if no local

    try:
        # create_all uses checkfirst=True by default, but we add error handling for edge cases
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except ProgrammingError as e:
        # Handle cases where objects already exist (idempotent operation)
        if "already exists" in str(e).lower():
            print(f"Database objects already exist (this is normal on restart): {e}")
        else:
            # Re-raise if it's a different error
            raise
