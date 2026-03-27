# Skill: Implementar Feature

Flujo profesional para implementar una nueva funcionalidad en TechStock.

## Instrucciones

Sigue este flujo estricto de desarrollo:

### 1. Analisis (Plan)
- Lee CLAUDE.md para entender convenciones y patrones
- Usa agente Explore para investigar codigo relacionado
- Identifica archivos a modificar/crear
- Presenta el plan al usuario antes de implementar

### 2. Implementacion (por orden)
- **Modelo** (models.py): agregar/modificar modelo SQLAlchemy
- **Migracion** (migrations.py): agregar migracion idempotente si se cambia schema
- **Router** (routers/<modulo>.py): seguir patron CRUD estandar del proyecto
- **Templates** (templates/<modulo>/): seguir patron de herencia base.html
- **Sidebar** (templates/base.html): agregar enlace si es modulo nuevo
- **Auth** (auth.py): agregar modulo a MODULOS_DISPONIBLES si es nuevo
- **Main** (main.py): registrar router si es nuevo

### 3. Testing
- Crear tests en tests/test_<modulo>.py
- Agregar fixtures necesarias en tests/conftest.py
- Ejecutar `pytest` y verificar 100% verde

### 4. Verificacion
- Ejecutar /simplify para revisar calidad
- Verificar que CSRF esta en todos los formularios POST
- Verificar que log_audit() esta en todos los CREATE/UPDATE/DELETE
- Verificar soft delete (nunca db.delete())

## Feature solicitada
$ARGUMENTS
