# Refactorizar Codigo

Reestructurar codigo existente sin cambiar comportamiento.

## Agente: developer
## Skills: checklist-techstock.md

## Instrucciones
- Mapear todas las dependencias del codigo objetivo (imports, usos, tests)
- Ejecutar `pytest --tb=short -q` ANTES — si falla, parar y reportar
- Presentar plan: que cambia, que no cambia, nivel de riesgo
- Ejecutar refactor en orden de dependencias (hojas primero, raiz al final)
- Ejecutar `pytest --tb=short -q` DESPUES — misma cantidad de tests, todos verdes
- Verificar imports: `python -c "from main import app"`

## Argumentos
$ARGUMENTS
