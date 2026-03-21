"""
Migraciones ligeras para TechStock.
Maneja ALTER TABLE de forma idempotente sin necesidad de Alembic.
Se ejecuta al iniciar la app, después de create_all().
"""
from sqlalchemy import text, inspect


def get_table_columns(conn, table_name: str) -> set:
    """Obtiene los nombres de columnas de una tabla."""
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


def table_exists(conn, table_name: str) -> bool:
    """Verifica si una tabla existe."""
    result = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name}
    )
    return result.fetchone() is not None


def run_migrations(engine):
    """Ejecuta migraciones pendientes de forma idempotente."""
    migrations_applied = 0

    with engine.connect() as conn:
        # ── Fase 3: Agregar cliente_id a facturas ──
        if table_exists(conn, "facturas"):
            columns = get_table_columns(conn, "facturas")
            if "cliente_id" not in columns:
                conn.execute(text("ALTER TABLE facturas ADD COLUMN cliente_id INTEGER NULL"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] facturas: agregada columna cliente_id")

        # ── Fase 4: Agregar venta_id a movimientos_inventario ──
        if table_exists(conn, "movimientos_inventario"):
            columns = get_table_columns(conn, "movimientos_inventario")
            if "venta_id" not in columns:
                conn.execute(text("ALTER TABLE movimientos_inventario ADD COLUMN venta_id INTEGER NULL"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] movimientos_inventario: agregada columna venta_id")

    if migrations_applied > 0:
        print(f"  [Migration] {migrations_applied} migración(es) aplicada(s)")
    return migrations_applied
