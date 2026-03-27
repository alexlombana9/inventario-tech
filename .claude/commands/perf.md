# Skill: Analisis de Rendimiento

Identifica y resuelve cuellos de botella de rendimiento.

## Instrucciones

### 1. Scope
- Con argumento: analizar archivo/modulo especifico
- Sin argumento: analisis completo del proyecto

### 2. Analisis de queries (prioridad alta)
- Buscar N+1 queries: loops que ejecutan queries dentro (`for item in items: db.query(...)`)
- Verificar que joins/joinedload se usan donde hay relaciones
- Buscar queries sin filtro de paginacion en listados
- Verificar indices en columnas usadas en WHERE/JOIN/ORDER BY
- Buscar `db.query(Model).all()` sin filtros (carga tabla completa)
- Revisar dashboard queries (main.py) — son las mas pesadas

### 3. Analisis de endpoints
- Identificar endpoints que ejecutan multiples queries secuenciales que podrian consolidarse
- Buscar queries redundantes (misma query ejecutada multiples veces en un request)
- Verificar que `/ventas/api/*` (POS JSON) son rapidos — son criticos para UX
- Buscar operaciones de archivo sincronas que deberian ser async (aiofiles)

### 4. Analisis de templates
- Buscar logica pesada en templates (deberia estar en el router)
- Verificar que assets estaticos usan cache headers
- Buscar templates que cargan datos no necesarios

### 5. Analisis de base de datos
- Verificar pool_size y max_overflow para la carga esperada
- Buscar transacciones largas que bloquean otras operaciones
- Verificar que with_for_update() solo se usa donde es necesario
- Buscar oportunidades de agregar indices compuestos

### 6. Optimizaciones
Para cada problema encontrado:
- **Impacto**: alto/medio/bajo
- **Esfuerzo**: trivial/moderado/complejo
- **Fix**: codigo concreto o estrategia
- Priorizar por ratio impacto/esfuerzo

### 7. Implementar fixes
Si el usuario lo autoriza, aplicar las optimizaciones de mayor impacto:
- Ejecutar tests ANTES y DESPUES de cada cambio
- No sacrificar legibilidad por micro-optimizaciones
- Documentar cambios significativos

## Scope de analisis
$ARGUMENTS
