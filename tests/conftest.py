# ============================================================================
# tests/conftest.py - Pytest fixtures for testing
# ============================================================================

import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app modules
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32chars!!"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from shared.db_models import Base
from shared.deps import get_db
from utils.auth import create_access_token

# Create test database engine
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session: Session):
    """Override the get_db dependency for testing"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    return _override_get_db


@pytest.fixture
def auth_headers_admin() -> dict:
    """Generate auth headers for admin user"""
    token = create_access_token({"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_operator() -> dict:
    """Generate auth headers for operator user"""
    token = create_access_token({"sub": "operator", "role": "operator"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_viewer() -> dict:
    """Generate auth headers for viewer user"""
    token = create_access_token({"sub": "viewer", "role": "viewer"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_device_data() -> dict:
    """Sample device data for testing"""
    return {
        "hostname": "test-router-01",
        "vendor": "nokia",
        "ip": "192.168.1.1",
        "port": 830,
        "username": "admin",
        "password": "secret123"
    }


@pytest.fixture
def sample_rule_data() -> dict:
    """Sample audit rule data for testing"""
    return {
        "name": "test-rule",
        "description": "Test rule for unit testing",
        "vendor": "nokia",
        "severity": "high",
        "category": "security",
        "xpath": "/configure/system",
        "expected_value": "enabled",
        "operator": "equals"
    }
