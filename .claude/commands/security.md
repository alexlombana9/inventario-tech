# Skill: Auditoria de Seguridad

Analisis completo de seguridad del proyecto siguiendo OWASP Top 10.

## Instrucciones

### 1. Scope
- Si se recibe argumento, auditar solo ese archivo/modulo
- Sin argumento, auditar TODO el proyecto

### 2. Checklist OWASP (adaptar a contexto SSR + FastAPI)

**A01 — Broken Access Control:**
- Todos los endpoints tienen `require_auth` o `require_permiso`
- SUPERADMIN bypass es correcto (no expone datos entre locales sin seleccion)
- `get_local_id()` se usa en TODAS las queries que tocan datos de tenant
- No hay endpoints sin proteccion que deberian tenerla
- Verificar que POST endpoints no aceptan local_id del formulario (debe venir del server)

**A02 — Cryptographic Failures:**
- Passwords hasheadas con bcrypt (nunca plaintext, MD5, SHA)
- Cookies firmadas con clave secreta segura (no hardcodeada)
- `.secret_key` en .gitignore
- No hay secrets en codigo fuente ni templates

**A03 — Injection:**
- SQLAlchemy ORM usado en todas las queries (no raw SQL sin parametros)
- Templates Jinja2 con autoescaping (no `| safe` sin justificacion)
- No hay eval(), exec(), o subprocess con input de usuario
- Nombres de archivo sanitizados en uploads

**A04 — Insecure Design:**
- CSRF token en TODOS los formularios POST
- Patron PRG (Post-Redirect-Get) en todas las mutaciones
- Soft delete (nunca db.delete())
- Audit log en todas las mutaciones
- Transacciones atomicas en operaciones financieras

**A05 — Security Misconfiguration:**
- Debug mode deshabilitado en produccion
- CORS no es permisivo innecesariamente
- Headers de seguridad presentes
- Error pages no exponen stack traces al usuario

**A07 — Auth Failures:**
- Session cookies: HttpOnly, SameSite=Lax
- Session timeout configurado (8h max)
- No hay enumeracion de usuarios en login

**A09 — Logging & Monitoring:**
- AuditLog registra TODAS las mutaciones
- Logs incluyen IP, usuario, accion, entidad

### 3. Busqueda automatizada
Ejecuta estas busquedas en el codigo:
```
grep -r "db.delete" routers/              # Hard deletes prohibidos
grep -r "| safe" templates/               # XSS potencial
grep -r "text(" routers/ utils/           # Raw SQL
grep -r "eval\|exec" *.py routers/        # Code injection
grep -r "secret\|password\|key" --include="*.py" | grep -v test | grep -v hash
```

### 4. Reporte
Presenta hallazgos por severidad:
- **CRITICO** (parchar YA): vulnerabilidades explotables
- **ALTO**: debilidades de seguridad importantes
- **MEDIO**: mejoras de hardening recomendadas
- **BAJO**: mejores practicas opcionales

Incluye: archivo, linea, descripcion, fix sugerido.

## Scope de auditoria
$ARGUMENTS
