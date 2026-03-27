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

        # ── Crear índices de rendimiento ──
        _perf_indexes = [
            ("ix_productos_categoria_id", "productos", "categoria_id"),
            ("ix_productos_proveedor_id", "productos", "proveedor_id"),
            ("ix_productos_activo", "productos", "activo"),
            ("ix_mov_inv_producto_id", "movimientos_inventario", "producto_id"),
            ("ix_mov_inv_fecha", "movimientos_inventario", "fecha"),
            ("ix_mov_inv_proveedor_id", "movimientos_inventario", "proveedor_id"),
            ("ix_ventas_fecha", "ventas", "fecha"),
            ("ix_ventas_estado", "ventas", "estado"),
            ("ix_ventas_vendedor_id", "ventas", "vendedor_id"),
            ("ix_ventas_caja_id", "ventas", "caja_id"),
            ("ix_ventas_cliente_id", "ventas", "cliente_id"),
            ("ix_detalle_venta_venta_id", "detalle_venta", "venta_id"),
            ("ix_detalle_venta_producto_id", "detalle_venta", "producto_id"),
            ("ix_deudas_estado", "deudas", "estado"),
            ("ix_deudas_acreedor_id", "deudas", "acreedor_id"),
            ("ix_deudas_proveedor_id", "deudas", "proveedor_id"),
            ("ix_facturas_estado", "facturas", "estado"),
            ("ix_facturas_fecha_emision", "facturas", "fecha_emision"),
            ("ix_gastos_activo", "gastos", "activo"),
            ("ix_gastos_fecha", "gastos", "fecha"),
            ("ix_cajas_usuario_id", "cajas", "usuario_id"),
            ("ix_cajas_estado", "cajas", "estado"),
            ("ix_mov_caja_caja_id", "movimientos_caja", "caja_id"),
            ("ix_pagos_deuda_deuda_id", "pagos_deuda", "deuda_id"),
            ("ix_cobros_factura_factura_id", "cobros_factura", "factura_id"),
            ("ix_clientes_activo", "clientes", "activo"),
            ("ix_clientes_documento", "clientes", "documento"),
            ("ix_usuarios_activo", "usuarios", "activo"),
            ("ix_audit_log_created_at", "audit_log", "created_at"),
            ("ix_audit_log_accion", "audit_log", "accion"),
        ]
        for idx_name, tbl, col in _perf_indexes:
            if table_exists(conn, tbl):
                exists = conn.execute(text(
                    "SELECT 1 FROM pg_indexes WHERE indexname = :name"
                ), {"name": idx_name}).first()
                if not exists:
                    conn.execute(text(f"CREATE INDEX {idx_name} ON {tbl} ({col})"))
                    migrations_applied += 1
        if migrations_applied > 0:
            conn.commit()
            print(f"  [Migration] Índices de rendimiento creados")

    if migrations_applied > 0:
        print(f"  [Migration] {migrations_applied} migración(es) aplicada(s)")
    return migrations_applied
