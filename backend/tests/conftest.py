import os

# Must be set before the app is imported, because settings are read on first use.
os.environ.setdefault("SECRET_KEY", "test-secret-key-used-only-in-tests-0123456789")

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.anti_spam import get_submission_limiter
from app.core.config import Settings, get_settings
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.repositories.admin_repository import AdminRepository
from app.services.auth_service import AuthService

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "correct-horse-battery"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 64


class IsolatedSettings(Settings):
    """Settings for tests: only the values given in code, never the developer's .env file or environment.

    Without this, tests would pick up a real GEMINI_API_KEY from backend/.env, call the real API and
    behave differently on every machine.
    """

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return (init_settings,)


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """A test that tries to reach the internet fails loudly instead of using real keys and quota."""

    def refuse(self, request):
        raise AssertionError(f"Tests must not use the network (tried {request.url})")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return IsolatedSettings(
        secret_key="test-secret-key-used-only-in-tests-0123456789",
        database_url="sqlite://",
        upload_dir=tmp_path / "uploads",
        max_photo_bytes=2048,
    )


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory, settings) -> TestClient:
    app = create_app()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings
    # A fresh, generous limiter per test, so rate limiting never interferes with other tests.
    limiter = SlidingWindowRateLimiter(max_requests=1000, window_seconds=3600)
    app.dependency_overrides[get_submission_limiter] = lambda: limiter
    return TestClient(app)


@pytest.fixture
def admin_headers(client, session_factory, settings) -> dict[str, str]:
    with session_factory() as db:
        AuthService(db, AdminRepository(db), settings).create_admin(ADMIN_USERNAME, ADMIN_PASSWORD)
    response = client.post(
        "/api/admin/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def submit(client):
    """Submit a complaint with sensible defaults; pass keyword arguments to override them."""

    def _submit(photo: tuple | None = None, **overrides):
        form = {
            "description": "Large pothole near the main market crossing.",
            "latitude": "31.5204",
            "longitude": "74.3587",
            **overrides,
        }
        files = {"photo": photo} if photo else None
        return client.post("/api/complaints", data=form, files=files)

    return _submit
