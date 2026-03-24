# TechStock - Convenciones del Proyecto

## Stack Tecnologico
- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- **Frontend**: Jinja2 Templates + Bootstrap 5 + Vanilla JS
- **Auth**: Cookies firmadas (itsdangerous) + bcrypt
- **Testing**: pytest + httpx + SQLite in-memory

## Estructura del Proyecto
```
main.py              → App FastAPI, dashboard, startup
database.py          → Engine, SessionLocal, Base, get_db
models.py            → Todos los modelos SQLAlchemy (16 tablas)
auth.py              → Hash, cookies, sesion, audit, require_role
middleware.py         → AuthMiddleware (cookie → request.state.user)
templates_config.py   → Instancia Jinja2 + filtros custom
seed.py              → Datos iniciales (admin, config)
migrations.py        → Migraciones idempotentes
routers/             → Un archivo por modulo de negocio
templates/           → Jinja2 HTML, organizados por modulo
static/css|js/       → CSS y JS del frontend
tests/               → pytest, conftest.py con fixtures
```

## Convenciones de Codigo

### Backend (Python)
- Routers: un archivo por entidad/modulo en `routers/`
- Nombres de rutas en espanol (lista, nuevo, editar, eliminar, detalle)
- Todos los POST retornan RedirectResponse 303 (PRG pattern)
- Auth: `require_auth` para login, `require_role("ADMIN")` para roles
- Audit: llamar `log_audit()` en operaciones CREATE/UPDATE/DELETE
- Flash messages via `set_flash()` (cookies firmadas)

### Frontend (Templates)
- Herencia: todos extienden `base.html`
- Bloques: `title`, `page_title`, `content`, `scripts`
- Filtros custom: `{{ valor | moneda }}`, `{{ valor | numero }}`

### Base de Datos
- Soft delete: campos `activo = Boolean` en vez de DELETE fisico
- Timestamps: `created_at`, `updated_at` con `datetime.now`
- IDs: Integer autoincremental

### Testing
- Tests en `tests/test_<modulo>.py`
- Fixtures en `tests/conftest.py`
- DB: SQLite in-memory con StaticPool
- Env: `TESTING=1` desactiva init de produccion
- Ejecutar: `pytest` desde la raiz del proyecto

## Comandos
```bash
# Desarrollo
python main.py                    # Iniciar servidor
pip install -r requirements-dev.txt  # Instalar con deps de test

# Testing
pytest                            # Ejecutar todos los tests
pytest tests/test_ventas.py -v    # Un modulo especifico
pytest --cov --cov-report=html    # Con reporte de cobertura
```
