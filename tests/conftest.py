import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # one in-memory database shared across connections for the whole test
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    engine.connect().exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    """Register a user and return headers with a bearer token."""

    def _make(email="ann@example.com", password="correct horse"):
        client.post("/api/auth/register", json={"email": email, "password": password})
        token = client.post("/api/auth/login", json={"email": email, "password": password}).json()
        return {"Authorization": f"Bearer {token['access_token']}"}

    return _make
