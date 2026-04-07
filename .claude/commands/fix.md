# Corregir Bug

Diagnosticar y corregir bugs con enfoque TDD.

## Agente: developer
## Skills: testing-guide.md, checklist-techstock.md

## Instrucciones
- Diagnosticar la causa raiz leyendo archivos relevantes completos
- Escribir un test que reproduzca el bug ANTES de corregirlo (debe fallar)
- Aplicar el fix minimo necesario, sin refactors innecesarios
- Ejecutar `pytest --tb=short -q` y verificar que todo pasa
- Validar checklist si el fix toca POST/datos: CSRF, audit, soft delete, local_id

## Argumentos
$ARGUMENTS
