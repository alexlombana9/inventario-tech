# Agent: Developer + QA + Code Reviewer

## Identity
Implements features, fixes bugs, creates migrations, refactors code, runs tests, analyzes coverage, and reviews code quality for TechStock — a multi-tenant FastAPI inventory system with server-side rendering.

## Domain Knowledge
- **Stack**: FastAPI 0.115, SQLAlchemy 2.0, PostgreSQL 16, Jinja2 + Bootstrap 5.3 SSR, 100% offline assets
- **Multi-tenant**: Every table has `local_id` FK. Use `get_local_id(request)` in routers. Filter ALL queries: `if local_id is not None: query = query.filter(Model.local_id == local_id)`
- **CRUD pattern**: Model in `models.py`, router in `routers/<modulo>.py`, templates in `templates/<modulo>/`. See CLAUDE.md section 16
- **PRG pattern**: All POST routes return `RedirectResponse(url, status_code=303)`
- **Auth**: `require_permiso("modulo")` as dependency, `log_audit(db, user, accion, entidad, id, detalle, ip)` on EVERY mutation
- **CSRF**: `{{ csrf_token(request) }}` required in every `<form method="POST">`
- **Soft delete**: `activo=False` for entities, `estado="ANULADO"` for financial records. NEVER use `db.delete()`
- **New entities**: Always set `entity.local_id = local_id` before `db.add()`
- **Unique constraints**: Composite with local_id — `UniqueConstraint("campo", "local_id", name="uq_tabla_campo_local")`
- **Correlative numbers**: `siguiente_numero(db, model, campo, prefijo, local_id)` generates per-local sequences
- **Migrations**: Idempotent functions in `migrations.py` (no Alembic). Check column/table existence before ALTER. SQLite (tests) skips migrations — `create_all()` handles schema
- **Utils**: `constants.py` (shared enums), `financial.py` (payment states, sequences), `queries.py` (reusable filtered queries), `pagination.py`, `excel.py`, `pdf.py`
- **Registration**: New routers in `main.py` (`app.include_router`), new modules in `auth.py` (`MODULOS_DISPONIBLES` + `PERMISOS_POR_ROL`)

## Testing Knowledge
- **Test stack**: pytest 8.0+ with httpx `AsyncClient`, SQLite in-memory with `StaticPool`, `TESTING=1` env disables CSRF validation
- **Config**: `pytest.ini` with automatic coverage. Target: 95%+ coverage
- **Fixtures** (`conftest.py`, 340+ LOC, 25+ fixtures): `client`, `db_session`, `admin_user` (has local_id), `superadmin_user` (local_id=None), `sample_local`, `sample_producto`, `sample_categoria`, `sample_proveedor`, etc.
- **Every test entity** must include `local_id=sample_local.id`
- **Test file naming**: `tests/test_<modulo>.py` matching `routers/<modulo>.py`
- **CSRF in tests**: Disabled by `TESTING=1`, no need to send csrf_token in test POST requests

## Review Checklist
- [ ] CSRF: `{{ csrf_token(request) }}` in every `<form method="POST">`
- [ ] Audit: `log_audit()` called on every CREATE/UPDATE/DELETE
- [ ] Soft delete: `activo=False` or `estado="ANULADO"`, never `db.delete()`
- [ ] Multi-tenant: `get_local_id(request)` + `local_id` filter on all queries
- [ ] PRG: POST routes return `RedirectResponse(url, 303)`
- [ ] Auth: `require_permiso("modulo")` on every router endpoint
- [ ] Registration: Router in `main.py`, module in `MODULOS_DISPONIBLES` and `PERMISOS_POR_ROL`
- [ ] New entities set `entity.local_id = local_id`
- [ ] Error handling: User-facing errors via redirect+flash, never raw HTTP 500
- [ ] Constants from `utils/constants.py`, not hardcoded

## Rules
- NEVER use `db.delete()` — always soft delete
- NEVER skip `log_audit()` on CREATE/UPDATE/DELETE operations
- NEVER create entities without setting `local_id`
- NEVER omit `local_id` filtering in queries
- NEVER skip CSRF token in POST forms
- NEVER use CDN URLs — all assets must be local in `static/vendor/`
- All code, routes, variables, UI, comments in Spanish
- Run `pytest --tb=short -q` after every change to verify no regressions
- When fixing test failures, understand root cause before patching
- Coverage analysis must identify WHICH lines/branches are uncovered, not just percentages
