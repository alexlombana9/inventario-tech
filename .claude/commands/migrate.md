# Skill: Crear Migracion de Base de Datos

Genera migraciones idempotentes para PostgreSQL siguiendo el patron del proyecto (sin Alembic).

## Instrucciones

### 1. Entender el cambio
- Parsear el argumento: que tabla/columna/constraint se necesita
- Leer `models.py` para ver el estado actual del modelo
- Leer `migrations.py` para ver migraciones existentes y seguir el patron

### 2. Actualizar modelo (models.py)
- Agregar/modificar la columna o tabla en el modelo SQLAlchemy
- Si es tabla nueva: incluir `local_id = Column(Integer, ForeignKey("locales.id"))`
- Si es columna nueva: definir tipo, default, nullable
- Respetar convenciones: `activo` para soft delete, timestamps, etc.

### 3. Crear migracion (migrations.py)
Seguir el patron idempotente del proyecto:

```python
# Dentro de run_migrations():
if table_exists(conn, "tabla"):
    columns = get_table_columns(conn, "tabla")
    if "nueva_columna" not in columns:
        conn.execute(text(
            "ALTER TABLE tabla ADD COLUMN nueva_columna TIPO DEFAULT valor"
        ))
        logger.info("Migracion: agregada columna nueva_columna a tabla")
```

**Reglas:**
- SIEMPRE verificar existencia antes de alterar (idempotente)
- Solo PostgreSQL — SQLite usa `create_all()` en tests
- Usar `text()` de SQLAlchemy para SQL raw
- Incluir `logger.info()` para trazar la migracion
- Si agrega FK: verificar que la tabla referenciada existe
- Si agrega unique constraint compuesta con local_id: usar `UniqueConstraint`
- Si necesita backfill: hacerlo en la misma migracion

### 4. Verificar
- Ejecutar `pytest --tb=short -q` — tests usan SQLite con create_all(), deben pasar
- Verificar que el modelo y la migracion son coherentes
- Si la migracion toca datos existentes, verificar que el backfill es correcto

## Cambio solicitado
$ARGUMENTS
