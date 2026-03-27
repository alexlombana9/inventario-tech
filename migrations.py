"""
Migraciones ligeras para TechStock (PostgreSQL).
Maneja ALTER TABLE de forma idempotente sin necesidad de Alembic.
Se ejecuta al iniciar la app, después de create_all().
"""
from sqlalchemy import text


def get_table_columns(conn, table_name: str) -> set:
    """Obtiene los nombres de columnas de una tabla (PostgreSQL)."""
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :table_name"
    ), {"table_name": table_name})
    return {row[0] for row in result.fetchall()}


def table_exists(conn, table_name: str) -> bool:
    """Verifica si una tabla existe (PostgreSQL)."""
    result = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT FROM information_schema.tables "
        "  WHERE table_name = :name"
        ")"
    ), {"name": table_name})
    return result.scalar()


def run_migrations(engine):
    """Ejecuta migraciones pendientes de forma idempotente (PostgreSQL).

    En tests (SQLite in-memory), create_all() maneja el schema completo.
    """
    url_str = str(engine.url)
    if url_str.startswith("sqlite"):
        return 0

    migrations_applied = 0

    with engine.connect() as conn:
        # ── Agregar cliente_id a facturas ──
        if table_exists(conn, "facturas"):
            columns = get_table_columns(conn, "facturas")
            if "cliente_id" not in columns:
                conn.execute(text("ALTER TABLE facturas ADD COLUMN cliente_id INTEGER NULL"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] facturas: agregada columna cliente_id")

        # ── Agregar venta_id a movimientos_inventario ──
        if table_exists(conn, "movimientos_inventario"):
            columns = get_table_columns(conn, "movimientos_inventario")
            if "venta_id" not in columns:
                conn.execute(text("ALTER TABLE movimientos_inventario ADD COLUMN venta_id INTEGER NULL"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] movimientos_inventario: agregada columna venta_id")

        # ── Crear tabla acreedores ──
        if not table_exists(conn, "acreedores"):
            conn.execute(text("""
                CREATE TABLE acreedores (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(200) NOT NULL,
                    tipo VARCHAR(20) DEFAULT 'OTRO',
                    documento VARCHAR(50) DEFAULT '',
                    telefono VARCHAR(50) DEFAULT '',
                    email VARCHAR(100) DEFAULT '',
                    direccion TEXT DEFAULT '',
                    notas TEXT DEFAULT '',
                    activo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX ix_acreedores_id ON acreedores (id)"))
            conn.commit()
            migrations_applied += 1
            print("  [Migration] acreedores: tabla creada")

        # ── Agregar referencia y precio_venta_minimo a productos ──
        if table_exists(conn, "productos"):
            columns = get_table_columns(conn, "productos")
            if "referencia" not in columns:
                conn.execute(text("ALTER TABLE productos ADD COLUMN referencia VARCHAR(100) DEFAULT ''"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] productos: agregada columna referencia")
            if "precio_venta_minimo" not in columns:
                conn.execute(text("ALTER TABLE productos ADD COLUMN precio_venta_minimo FLOAT DEFAULT 0.0"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] productos: agregada columna precio_venta_minimo")

        # ── Agregar precio_costo a detalle_venta ──
        if table_exists(conn, "detalle_venta"):
            columns = get_table_columns(conn, "detalle_venta")
            if "precio_costo" not in columns:
                conn.execute(text("ALTER TABLE detalle_venta ADD COLUMN precio_costo FLOAT DEFAULT 0.0"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] detalle_venta: agregada columna precio_costo")

        # ── Agregar acreedor_id a deudas ──
        if table_exists(conn, "deudas"):
            columns = get_table_columns(conn, "deudas")
            if "acreedor_id" not in columns:
                conn.execute(text("ALTER TABLE deudas ADD COLUMN acreedor_id INTEGER NULL"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] deudas: agregada columna acreedor_id")

        # ── Agregar email y telefono a usuarios ──
        if table_exists(conn, "usuarios"):
            columns = get_table_columns(conn, "usuarios")
            if "email" not in columns:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) DEFAULT ''"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] usuarios: agregada columna email")
            if "telefono" not in columns:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(50) DEFAULT ''"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] usuarios: agregada columna telefono")

        # ── Agregar foto a usuarios ──
        if table_exists(conn, "usuarios"):
            columns = get_table_columns(conn, "usuarios")
            if "foto" not in columns:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN foto VARCHAR(255) DEFAULT ''"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] usuarios: agregada columna foto")

        # ── Agregar permisos a usuarios ──
        if table_exists(conn, "usuarios"):
            columns = get_table_columns(conn, "usuarios")
            if "permisos" not in columns:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN permisos TEXT DEFAULT ''"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] usuarios: agregada columna permisos")

        # ── Agregar activo a categorias (soft delete) ──
        if table_exists(conn, "categorias"):
            columns = get_table_columns(conn, "categorias")
            if "activo" not in columns:
                conn.execute(text("ALTER TABLE categorias ADD COLUMN activo BOOLEAN DEFAULT TRUE"))
                conn.commit()
                migrations_applied += 1
                print("  [Migration] categorias: agregada columna activo")

    if migrations_applied > 0:
        print(f"  [Migration] {migrations_applied} migración(es) aplicada(s)")
    return migrations_applied
