# Analisis de Rendimiento

Identificar y resolver cuellos de botella de rendimiento.

## Agente: ops
## Skills: performance-analysis.md

## Instrucciones
- Definir scope: con argumento analizar ese modulo, sin argumento analisis completo
- Analizar queries: N+1, falta de joins/joinedload, queries sin paginacion, sin indices
- Analizar endpoints: queries redundantes, operaciones sync que deberian ser async
- Analizar DB: pool_size, transacciones largas, indices compuestos faltantes
- Priorizar por ratio impacto/esfuerzo — implementar solo si el usuario autoriza

## Argumentos
$ARGUMENTS
