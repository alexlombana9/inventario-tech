# Skill: Estado del Proyecto

Muestra un resumen completo del estado actual del proyecto TechStock.

## Instrucciones

Ejecuta los siguientes comandos y presenta un reporte estructurado:

1. **Git status**: `git status` + `git log --oneline -10`
2. **Tests**: `pytest --tb=short -q` (ejecutar y reportar resultados)
3. **Archivos modificados**: listar cambios pendientes de commit
4. **Conteo de codigo**:
   - Total de routers: contar archivos en routers/
   - Total de templates: contar archivos en templates/
   - Total de tests: contar tests con `pytest --collect-only -q`
5. **Issues conocidos**: leer memory/project_critical_issues.md si existe

Presenta todo en formato de tabla/reporte limpio y conciso.
