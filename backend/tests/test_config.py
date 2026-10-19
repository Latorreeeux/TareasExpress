import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("overrides", [
    {"app_env": "production"}, {"database_url": "postgresql://localhost/db"},
    {"database_url": "sqlite:///:memory:"}, {"max_upload_bytes": 0},
    {"max_request_bytes": 1}, {"sqlite_busy_timeout_ms": -1},
    {"cors_origins": ["*"]}, {"cors_origins": ["https://example.com"]},
])
def test_invalid_configuration(overrides):
    with pytest.raises((ValidationError, ValueError)):
        Settings(_env_file=None, **overrides)


def test_local_configuration():
    settings = Settings(_env_file=None, cors_origins=["http://localhost:5173"])
    assert settings.app_env == "local"
    assert settings.max_files_per_request == 10


def test_app_startup_and_no_implicit_seed():
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get('/openapi.json').status_code == 200
