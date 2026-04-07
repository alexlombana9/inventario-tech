# Checklist TechStock — Reglas Obligatorias

## Seguridad
- [ ] CSRF: `{{ csrf_token(request) }}` en todo `<form method="POST">`
- [ ] Auth: `require_permiso("modulo")` o `require_auth` en cada endpoint
- [ ] Passwords: bcrypt via `hash_password()`, nunca plaintext
- [ ] Cookies: HttpOnly, SameSite=Lax, firmadas con itsdangerous
- [ ] No secrets en codigo fuente ni templates

## Multi-Tenant
- [ ] `local_id = get_local_id(request)` al inicio de cada endpoint
- [ ] `if local_id is not None: query = query.filter(Model.local_id == local_id)`
- [ ] `entity.local_id = local_id` al crear cualquier entidad
- [ ] `local_id` NUNCA viene del formulario/usuario — siempre del server
- [ ] UniqueConstraint compuesta con local_id para unicidad por tenant

## Datos
- [ ] Soft delete: `activo=False` o `estado="ANULADO"` — NUNCA `db.delete()`
- [ ] `log_audit(db, user, accion, entidad, id, detalle, ip)` en todo CREATE/UPDATE/DELETE
- [ ] POST retorna `RedirectResponse(url, status_code=303)` — patron PRG
- [ ] Transacciones atomicas en operaciones financieras (try/except + rollback)

## Tests
- [ ] Toda entidad en tests incluye `local_id=sample_local.id`
- [ ] Fixtures de conftest.py: client, admin_user, superadmin_user, sample_local
- [ ] pytest con SQLite in-memory (TESTING=1, StaticPool)
- [ ] CSRF deshabilitado en tests (TESTING=1)
