"""SQLAlchemy engine and session setup (SQLite, single-file, local)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from . import config

config.ensure_dirs()

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},  # allow use across worker threads
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def init_db() -> None:
    """Create tables if they do not exist."""
    from . import models  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency yielding a request-scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
