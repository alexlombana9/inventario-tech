# Analisis de Rendimiento — TechStock

## Queries
- **N+1**: Buscar loops que ejecutan queries individuales — reemplazar con `joinedload()` o `subqueryload()`
- **Joins faltantes**: Queries que acceden a relaciones sin eager loading en listas/reportes
- **Sin paginar**: `query.all()` sin `paginate()` en endpoints que pueden crecer — usar `utils/pagination.py`
- **Indices faltantes**: Columnas usadas en WHERE/ORDER BY sin index — especialmente `local_id`, `activo`, `created_at`
- **Conteos costosos**: `len(query.all())` en vez de `query.count()`

## Endpoints
- **Queries redundantes**: Mismo dato consultado multiples veces en un request (ej: config, local)
- **Dashboard**: `main.py GET /` ejecuta 30+ queries — verificar que todas usan indices
- **POS**: `/ventas/api/*` debe ser rapido — buscar queries innecesarias en busqueda de productos
- **Reportes**: Queries de agregacion (SUM, COUNT, GROUP BY) sin indices compuestos
- **Exports**: Excel/PDF generados sincrona — verificar tamano de datos

## Templates
- **Logica pesada**: Calculos en Jinja2 que deberian estar en Python (props calculadas en modelo)
- **Datos innecesarios**: Queries que cargan campos que el template no usa
- **Assets**: Verificar que vendor/ (Bootstrap, Chart.js) usa versiones minificadas

## Base de Datos
- **Pool**: PostgreSQL configurado con pool_size=10, max_overflow=20 — ajustar segun carga
- **Transacciones largas**: `with_for_update()` solo donde es necesario (ventas, caja)
- **Indices compuestos**: `(local_id, activo)`, `(local_id, created_at)` para queries frecuentes
- **VACUUM/ANALYZE**: Soft deletes acumulan filas inactivas — considerar mantenimiento periodico

## Priorizacion de Fixes
| Impacto | Esfuerzo Bajo | Esfuerzo Alto |
|---------|---------------|---------------|
| **Alto** | Agregar indices, joinedload, paginate | Refactorizar dashboard queries |
| **Bajo** | Cache headers estaticos, minificar | Async file ops, connection pooling |

Prioridad: Alto impacto + bajo esfuerzo primero.
