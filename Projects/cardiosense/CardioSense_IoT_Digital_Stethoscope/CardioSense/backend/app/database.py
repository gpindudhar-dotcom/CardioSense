from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .models import Base

DEFAULT_DB = "sqlite:///./cardiosense.db"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB)


def create_db_engine():
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # create_all does not add columns to an existing SQLite database.
    if "owner_user_id" not in {column["name"] for column in inspect(engine).get_columns("recordings")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE recordings ADD COLUMN owner_user_id INTEGER REFERENCES users(id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_recordings_owner_user_id ON recordings (owner_user_id)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def recordings_dir() -> Path:
    raw = os.getenv("RECORDINGS_DIR", "../data/recordings")
    path = Path(raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
