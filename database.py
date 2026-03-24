import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Cargar .env si existe (sin dependencias externas) ─────────
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())

# ── Configuración de Base de Datos ────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/inventario"
)

_engine_kwargs = {"pool_pre_ping": True}
_connect_args = {}

if DATABASE_URL.startswith("postgresql"):
    _connect_args["client_encoding"] = "utf8"
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
elif DATABASE_URL.startswith("sqlite"):
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
    finally:
        db.close()
