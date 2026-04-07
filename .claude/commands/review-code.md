# Review de Codigo

Revisar cambios para calidad, seguridad y consistencia.

## Agente: qa
## Skills: checklist-techstock.md

## Instrucciones
- Obtener diff: `git diff` (o `git diff HEAD~1` si no hay cambios locales)
- Revisar seguridad: CSRF, no hard deletes, no raw SQL, endpoints protegidos
- Revisar calidad: log_audit en mutaciones, PRG 303, tests cubren cambios
- Revisar consistencia: rutas en espanol, convenciones de CLAUDE.md
- Reportar por severidad: critico > importante > menor

## Argumentos
$ARGUMENTS
