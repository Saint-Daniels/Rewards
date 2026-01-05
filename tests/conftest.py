"""Pytest configuration and fixtures"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from uuid import uuid4
import os

from src.db.connection import Base, get_db
from src.db.models import User
from src.api.routes import app

# Test database URL
TEST_DB_URL = os.getenv(
    "TEST_DB_CONNECTION_STRING",
    "postgresql://postgres:postgres@localhost:5432/rewards_test"
)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        external_core_id=str(uuid4()),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing"""
    return {
        "user_id": str(uuid4()),
        "sub": "test_user",
        "exp": 9999999999,
    }


@pytest.fixture
def authenticated_client(client, mock_jwt_token):
    """Client with mocked JWT authentication"""
    # Mock the JWT verifier
    from src.auth import jwt_verifier
    
    def mock_get_current_user():
        return mock_jwt_token
    
    app.dependency_overrides[jwt_verifier.get_current_user] = mock_get_current_user
    yield client
    app.dependency_overrides.clear()

