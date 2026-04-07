# Ejecutar Tests

Ejecutar y analizar la suite de tests de TechStock.

## Agente: qa
## Skills: testing-guide.md

## Instrucciones
- Sin args: `pytest --tb=short -q` (suite completa)
- Con modulo: `pytest tests/test_<arg>.py -v` (modulo especifico)
- Analizar resultados: si hay fallos, identificar causa raiz y sugerir fixes
- Si el argumento es "fix": corregir fallos automaticamente y re-ejecutar

## Argumentos
$ARGUMENTS
