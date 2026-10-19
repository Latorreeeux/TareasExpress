from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local"] = "local"
    database_url: str = "sqlite:///data/tareas.db"
    upload_dir: Path = Path("data/uploads")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_files_per_request: int = Field(default=10, gt=0)
    max_request_bytes: int = Field(default=101 * 1024 * 1024, gt=0)
    sqlite_busy_timeout_ms: int = Field(default=5000, gt=0)
    cors_origins: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def local_only(self):
        url = make_url(self.database_url)
        if url.drivername != "sqlite" or not url.database or url.database == ":memory:" or url.query:
            raise ValueError("DATABASE_URL debe usar SQLite en un archivo local sin opciones URI")
        if url.host or url.username or url.password:
            raise ValueError("SQLite debe ser local")
        if self.max_request_bytes < self.max_upload_bytes * self.max_files_per_request + 1024 * 1024:
            raise ValueError("MAX_REQUEST_BYTES debe cubrir los archivos y 1 MiB de multipart")
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
                raise ValueError("CORS solo permite orígenes locales explícitos")
        return self
