# Skill: Auditoria Completa del Proyecto

Barrido exhaustivo del estado de salud del proyecto: codigo, tests, seguridad, rendimiento y deuda tecnica.

## Instrucciones

Ejecutar TODAS las secciones en paralelo donde sea posible, luego consolidar.

### 1. Estado general
- `git status` + `git log --oneline -5`
- Contar: routers, templates, tests, modelos, endpoints
- Verificar que CLAUDE.md refleja el estado real

### 2. Tests y cobertura
```bash
pytest --cov --cov-report=term-missing --tb=short -q
```
- Reportar: total tests, pasados, fallidos, cobertura global
- Identificar los 5 archivos con menor cobertura

### 3. Consistencia de codigo
Verificar en paralelo con agentes Explore:
- Todos los routers usan `get_local_id()` y filtran por `local_id`
- Todos los POST tienen CSRF (`csrf_token` en templates)
- Todos los CREATE/UPDATE/DELETE tienen `log_audit()`
- Todos los deletes son soft delete (`activo=False` o `estado="ANULADO"`)
- Todos los POST retornan `RedirectResponse(..., 303)`
- Todos los routers registrados en `main.py`
- Todos los modulos en `MODULOS_DISPONIBLES` de `auth.py`

### 4. Codigo muerto y deuda tecnica
- Imports no usados
- Funciones definidas pero nunca llamadas
- Variables asignadas pero nunca leidas
- Templates sin ruta que las renderice
- Tests que prueban funcionalidad eliminada
- TODOs y FIXMEs en el codigo

### 5. Dependencias
- `pip list --outdated` (si es posible) o revisar requirements.txt contra versiones actuales
- Dependencias no usadas en requirements.txt
- Dependencias faltantes (importadas pero no en requirements)

### 6. Oportunidades de mejora
Identificar (sin implementar):
- Codigo duplicado que podria extraerse a utils/
- Queries repetidas que podrian ir a utils/queries.py
- Patrones inconsistentes entre routers
- Templates con logica que deberia estar en el backend

### 7. Reporte consolidado
Presentar en formato ejecutivo:

```
## Estado del Proyecto — [fecha]

### Metricas
| Metrica | Valor |
|---------|-------|
| Tests   | X passed, Y failed |
| Cobertura | X% |
| Routers | X |
| Endpoints | X |
| Modelos | X |

### Salud: [VERDE/AMARILLO/ROJO]

### Hallazgos criticos
1. ...

### Mejoras recomendadas (por prioridad)
1. ...

### Deuda tecnica
1. ...
```

## Scope
$ARGUMENTS
