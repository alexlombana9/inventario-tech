# Crear Migracion de Base de Datos

Generar migraciones idempotentes para PostgreSQL (sin Alembic).

## Agente: developer
## Skills: crud-pattern.md

## Instrucciones
- Entender el cambio solicitado y leer models.py + migrations.py
- Actualizar el modelo SQLAlchemy (incluir local_id si es tabla nueva)
- Crear migracion idempotente en migrations.py: verificar existencia antes de alterar
- Usar patron: `if table_exists → get_columns → if col not in columns → ALTER`
- Ejecutar `pytest --tb=short -q` para verificar (SQLite usa create_all, no migraciones)

## Argumentos
$ARGUMENTS
