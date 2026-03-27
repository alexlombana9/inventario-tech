# Skill: Ejecutar Tests

Ejecuta la suite de tests del proyecto TechStock.

## Instrucciones

1. Ejecuta `pytest` con las opciones apropiadas segun el argumento:
   - Sin argumentos: `pytest --tb=short -q` (suite completa, resumen corto)
   - Con argumento de modulo: `pytest tests/test_<arg>.py -v` (modulo especifico)
   - Con `--cov`: `pytest --cov --cov-report=term-missing --tb=short` (con cobertura)

2. Analiza los resultados:
   - Si todos pasan: reporta el conteo y cobertura
   - Si hay fallos: identifica la causa raiz de cada fallo, agrupa por tipo de error
   - Sugiere fixes concretos para cada fallo

3. Si el argumento es `fix`, ademas de ejecutar tests, corrige automaticamente los fallos encontrados y re-ejecuta para verificar.

## Argumento recibido
$ARGUMENTS
