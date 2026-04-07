# Auditoria de Seguridad

Analisis de seguridad siguiendo OWASP Top 10 adaptado a SSR + FastAPI.

## Agente: security
## Skills: security-owasp.md, checklist-techstock.md

## Instrucciones
- Definir scope: con argumento auditar ese archivo/modulo, sin argumento auditar todo
- Ejecutar checklist OWASP: access control, crypto, injection, CSRF, auth, logging
- Busqueda automatizada: db.delete, |safe, text(, eval/exec, secrets en codigo
- Reportar por severidad: CRITICO > ALTO > MEDIO > BAJO (archivo, linea, fix sugerido)

## Argumentos
$ARGUMENTS
