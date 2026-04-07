# Auditoria OWASP Top 10 — TechStock

## A01: Broken Access Control
- **Endpoints**: Todo endpoint usa `require_permiso()` o `require_auth`
- **RBAC**: SUPERADMIN > ADMIN > VENDEDOR/BODEGUERO — verificar en `auth.py` PERMISOS_POR_ROL
- **Multi-tenant**: Toda query filtra por `local_id` — un usuario NUNCA accede a datos de otro local
- **Buscar**: Endpoints sin `Depends(require_*)`, queries sin filtro `local_id`
- **Grep**: `@router\.(get|post)` sin `Depends(require_` en la misma funcion

## A02: Cryptographic Failures
- **Passwords**: bcrypt via `hash_password()`/`verify_password()` — nunca MD5/SHA/plaintext
- **Sesion**: Cookies firmadas con `itsdangerous.URLSafeTimedSerializer`
- **Secret key**: Archivo `.secret_key` (auto-generado), nunca en codigo fuente
- **Buscar**: `password` en plaintext, hardcoded secrets, `SECRET_KEY` en .py/.html

## A03: Injection
- **SQL**: SQLAlchemy ORM parametrizado — buscar `text()` con f-strings o .format()
- **XSS**: Jinja2 autoescaping activo — buscar `| safe`, `Markup()`, `{% autoescape false %}`
- **Command**: No hay subprocess con input de usuario — buscar `os.system`, `subprocess` con vars
- **Grep**: `text\(f"`, `\.format(`, `| safe`, `Markup(`, `eval(`, `exec(`

## A04: Insecure Design
- **CSRF**: Token en todo form POST — buscar `<form method="POST"` sin `csrf_token`
- **PRG**: Todo POST retorna redirect 303 — buscar POST que retorna template directo
- **Soft delete**: Nunca `db.delete()` — buscar `\.delete(` en routers
- **Audit**: `log_audit()` en toda mutacion — buscar POST sin `log_audit`
- **Atomicidad**: Ventas/pagos usan try/except + rollback

## A05: Security Misconfiguration
- **Debug**: `debug=True` no debe estar en produccion — verificar main.py, uvicorn config
- **CORS**: No configurado (SSR, no necesita) — verificar que no haya `CORSMiddleware` permisivo
- **Error pages**: Excepciones no exponen stack traces al usuario
- **Headers**: Verificar Content-Type, X-Content-Type-Options

## A07: Authentication Failures
- **Sesion**: Cookie expira en 8h (`SESSION_MAX_AGE`) — verificar en auth.py
- **Enumeracion**: Login no revela si el usuario existe vs password incorrecta
- **Brute force**: Sin rate limiting (pendiente) — documentar como riesgo aceptado
- **Multi-cuenta**: Cuentas guardadas en cookie (no exponen passwords)

## A09: Logging & Monitoring
- **AuditLog**: Toda mutacion registrada con usuario, IP, entidad, detalle, local_id
- **Cobertura**: Buscar routers POST sin `log_audit` — cada uno es una brecha
- **Grep**: `@router.post` seguido de bloque sin `log_audit`

## Patrones de Busqueda Automatizada
```bash
# Endpoints sin auth
grep -rn "@router\.\(get\|post\)" routers/ | grep -v "Depends(require_"
# Forms sin CSRF
grep -rn 'method="POST"' templates/ | grep -v "csrf_token"
# Hard deletes
grep -rn "\.delete(" routers/
# SQL injection risk
grep -rn 'text(f"' routers/ models.py main.py
# XSS risk
grep -rn "| safe" templates/
# Mutaciones sin audit
grep -rn "@router.post" routers/ # comparar con grep -rn "log_audit" routers/
```
