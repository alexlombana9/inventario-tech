# Crear Pull Request

Preparar y crear un Pull Request profesional con validaciones.

## Agente: release
## Skills: pr-workflow.md, checklist-techstock.md

## Instrucciones
- Validar: `git status`, `git diff --stat`, `pytest --tb=short -q` (si falla, PARAR)
- Si en main, crear rama: `git checkout -b <tipo>/<descripcion>` (feat/, fix/, refactor/, etc.)
- Commitear cambios pendientes con mensajes convencionales en espanol
- Push: `git push -u origin <rama>`
- Crear PR: `gh pr create` con resumen, cambios, tests, checklist TechStock
- Reportar URL del PR creado

## Argumentos
$ARGUMENTS
