# Auditoria Completa del Proyecto

Barrido exhaustivo de salud: codigo, tests, seguridad, rendimiento y deuda tecnica.

## Agente: release
## Skills: checklist-techstock.md, security-owasp.md, performance-analysis.md

## Instrucciones
- Estado general: git status, conteo de routers/templates/tests/modelos/endpoints
- Tests y cobertura: `pytest --cov --cov-report=term-missing --tb=short -q`
- Consistencia: verificar get_local_id, CSRF, log_audit, soft delete, PRG 303 en todos los routers
- Codigo muerto: imports no usados, funciones sin llamar, templates sin ruta, TODOs/FIXMEs
- Dependencias: requirements.txt vs imports reales, versiones desactualizadas
- Reporte consolidado: metricas, salud (VERDE/AMARILLO/ROJO), hallazgos, mejoras, deuda tecnica

## Argumentos
$ARGUMENTS
