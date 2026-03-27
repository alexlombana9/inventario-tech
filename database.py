"""
Configuracion de base de datos para TechStock.
PostgreSQL como motor principal. SQLite solo para tests (in-memory).
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Cargar .env si existe (sin dependencias externas) ─────────
if getattr(sys, "frozen", False):  # pragma: no cover
    _base_dir = os.path.dirname(sys.executable)  # pragma: no cover
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

_env_path = os.path.join(_base_dir, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())


def _default_database_url() -> str:
    """Retorna la URL de base de datos.

    - Si existe DATABASE_URL en entorno, la usa (PostgreSQL o SQLite para tests).
    - Si no, usa PostgreSQL local por defecto (modo standalone con PG portable).
    """
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url

    # Modo standalone: PostgreSQL portable en datos del usuario  # pragma: no cover
    if sys.platform == "win32":  # pragma: no cover
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))  # pragma: no cover
        data_dir = os.path.join(appdata, "TechStock")  # pragma: no cover
    else:  # pragma: no cover
        data_dir = os.path.join(os.path.expanduser("~"), ".techstock")  # pragma: no cover

    os.makedirs(data_dir, exist_ok=True)  # pragma: no cover
    return "postgresql://techstock:techstock@localhost:5433/techstock"  # pragma: no cover


# ── Configuracion de Base de Datos ────────────────────────────
DATABASE_URL = _default_database_url()

_engine_kwargs = {"pool_pre_ping": True}
_connect_args = {}

if DATABASE_URL.startswith("postgresql"):  # pragma: no cover
    _connect_args["client_encoding"] = "utf8"  # pragma: no cover
    _engine_kwargs["pool_size"] = 10  # pragma: no cover
    _engine_kwargs["max_overflow"] = 20  # pragma: no cover
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
