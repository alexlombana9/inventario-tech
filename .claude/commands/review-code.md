# Skill: Review de Codigo

Revisa el codigo modificado para calidad, seguridad y consistencia.

## Instrucciones

### 1. Obtener cambios
- Ejecuta `git diff` para ver cambios no commiteados
- Si no hay cambios locales, usa `git diff HEAD~1` para el ultimo commit

### 2. Revisar por categorias

**Seguridad:**
- Formularios POST tienen CSRF token: `{{ csrf_token(request) }}`
- No hay SQL raw sin parametrizar
- No hay hard deletes (debe usar activo=False o estado=ANULADO)
- Datos de usuario sanitizados (no inyeccion XSS)
- Endpoints protegidos con require_auth o require_role

**Calidad:**
- Todas las mutaciones tienen log_audit()
- POST routes retornan RedirectResponse 303 (patron PRG)
- No hay codigo duplicado que deberia estar en utils/
- Templates extienden base.html correctamente
- Tests cubren los cambios nuevos

**Consistencia:**
- Nombres de rutas en espanol
- Convenciones de CLAUDE.md respetadas
- Imports organizados (stdlib, third-party, local)

### 3. Reporte
Presenta los hallazgos organizados por severidad:
- **Critico**: problemas de seguridad o datos
- **Importante**: faltan tests, audit, o convenciones rotas
- **Menor**: estilo, organizacion, mejoras opcionales

## Scope del review
$ARGUMENTS
