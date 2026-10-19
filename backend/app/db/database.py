from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import Base


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})

        @event.listens_for(self.engine, "connect")
        def configure(connection, _):
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        @event.listens_for(self.engine, "begin")
        def explicit_begin(connection):
            mode = connection.get_execution_options().get("write_transaction", False)
            connection.exec_driver_sql("BEGIN IMMEDIATE" if mode else "BEGIN")

    def initialize(self):
        Path(make_url(self.settings.database_url).database).resolve().parent.mkdir(parents=True, exist_ok=True)
        uploads = self.settings.upload_dir.resolve()
        uploads.mkdir(parents=True, exist_ok=True)
        with self.engine.begin() as connection:
            Base.metadata.create_all(connection)

    @contextmanager
    def uow(self, *, write=False):
        with self.engine.connect().execution_options(write_transaction=write) as connection:
            with Session(bind=connection, expire_on_commit=False) as session:
                with session.begin():
                    yield session

    def dispose(self):
        self.engine.dispose()
