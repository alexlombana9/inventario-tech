"""
Configuracion de base de datos para TechStock.
PostgreSQL como motor principal. SQLite solo para tests (in-memory).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# ── Configuracion de Base de Datos ────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or settings.database_url

_engine_kwargs = {"pool_pre_ping": True}
_connect_args = {}

if DATABASE_URL.startswith("postgresql"):  # pragma: no cover
    _connect_args["client_encoding"] = "utf8"  # pragma: no cover
    _connect_args["connect_timeout"] = 5  # pragma: no cover
    _engine_kwargs["pool_size"] = 10  # pragma: no cover
    _engine_kwargs["max_overflow"] = 20  # pragma: no cover
    _engine_kwargs["pool_timeout"] = 30  # pragma: no cover
    _engine_kwargs["pool_recycle"] = 1800  # pragma: no cover
elif DATABASE_URL.startswith("sqlite"):
    # Solo para tests (SQLite in-memory)
    _connect_args["check_same_thread"] = False
    if DATABASE_URL == "sqlite://":
        from sqlalchemy.pool import StaticPool
        _engine_kwargs["poolclass"] = StaticPool

_engine_kwargs["connect_args"] = _connect_args

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
