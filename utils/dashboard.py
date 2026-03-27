"""Funciones helper para el dashboard. Extraídas de main.py para legibilidad y testabilidad."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date
from datetime import datetime, date, timedelta
import json
import models


def get_date_range(fecha_desde: str | None, fecha_hasta: str | None, hoy: date):
    """Parsea y retorna el rango de fechas para filtros del dashboard."""
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        except ValueError:
            fd = hoy - timedelta(days=30)
    else:
        fd = hoy - timedelta(days=30)

    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        except ValueError:
            fh = hoy
    else:
        fh = hoy

    fd_dt = datetime.combine(fd, datetime.min.time())
    fh_dt = datetime.combine(fh, datetime.max.time())
    return fd, fh, fd_dt, fh_dt


def get_general_metrics(db: Session):
    """Métricas generales que no dependen del rango de fechas."""
    P = models.Producto
    total_productos = db.query(func.count(P.id)).filter(P.activo == True).scalar() or 0
    total_proveedores = db.query(func.count(models.Proveedor.id)).filter(models.Proveedor.activo == True).scalar() or 0
    total_categorias = db.query(func.count(models.Categoria.id)).scalar() or 0
    total_clientes = db.query(func.count(models.Cliente.id)).filter(models.Cliente.activo == True).scalar() or 0
    stock_bajo = db.query(func.count(P.id)).filter(P.activo == True, P.stock_actual <= P.stock_minimo).scalar() or 0
    valor_inventario = db.query(func.sum(P.stock_actual * P.precio_costo)).filter(P.activo == True).scalar() or 0.0

    return {
        "total_productos": total_productos,
        "total_proveedores": total_proveedores,
        "total_categorias": total_categorias,
        "total_clientes": total_clientes,
        "stock_bajo": stock_bajo,
        "valor_inventario": valor_inventario,
    }


def get_period_metrics(db: Session, fd_dt: datetime, fh_dt: datetime):
    """Métricas de ventas y movimientos filtradas por período."""
    V = models.Venta
    DV = models.DetalleVenta
    MI = models.MovimientoInventario

    movimientos_periodo = db.query(func.count(MI.id)).filter(
        MI.fecha >= fd_dt, MI.fecha <= fh_dt
    ).scalar() or 0

    ventas_periodo = db.query(func.sum(V.total)).filter(
        V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
    ).scalar() or 0.0

    num_ventas_periodo = db.query(func.count(V.id)).filter(
        V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
    ).scalar() or 0

    ganancia_periodo = db.query(
        func.sum(DV.subtotal - DV.precio_costo * DV.cantidad)
    ).join(V).filter(
        V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
    ).scalar() or 0.0

    return {
        "movimientos_periodo": movimientos_periodo,
        "ventas_periodo": ventas_periodo,
        "num_ventas_periodo": num_ventas_periodo,
        "ganancia_periodo": round(ganancia_periodo, 2),
    }


def get_financial_metrics(db: Session):
    """Métricas financieras: deudas y facturas pendientes/vencidas."""
    ahora = datetime.now()

    deudas_pendientes_total = db.query(
        func.sum(models.Deuda.monto_total - models.Deuda.monto_pagado)
    ).filter(models.Deuda.estado != "PAGADO").scalar() or 0.0

    deudas_vencidas_count = db.query(func.count(models.Deuda.id)).filter(
        models.Deuda.estado != "PAGADO",
        models.Deuda.fecha_vencimiento != None,
        models.Deuda.fecha_vencimiento < ahora
    ).scalar() or 0

    facturas_por_cobrar_total = db.query(
        func.sum(models.Factura.monto_total - models.Factura.monto_cobrado)
    ).filter(models.Factura.estado != "PAGADO").scalar() or 0.0

    facturas_vencidas_count = db.query(func.count(models.Factura.id)).filter(
        models.Factura.estado != "PAGADO",
        models.Factura.fecha_vencimiento != None,
        models.Factura.fecha_vencimiento < ahora
    ).scalar() or 0

    return {
        "deudas_pendientes_total": deudas_pendientes_total,
        "deudas_vencidas_count": deudas_vencidas_count,
        "facturas_por_cobrar_total": facturas_por_cobrar_total,
        "facturas_vencidas_count": facturas_vencidas_count,
    }


def get_tables_data(db: Session):
    """Datos para tablas: últimos movimientos y productos con stock bajo."""
    ultimos_movimientos = db.query(models.MovimientoInventario).options(
        joinedload(models.MovimientoInventario.producto)
    ).order_by(
        models.MovimientoInventario.fecha.desc()
    ).limit(8).all()

    productos_stock_bajo = db.query(models.Producto).options(
        joinedload(models.Producto.categoria)
    ).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual <= models.Producto.stock_minimo
    ).order_by(models.Producto.stock_actual.asc()).limit(5).all()

    return {
        "ultimos_movimientos": ultimos_movimientos,
        "productos_stock_bajo": productos_stock_bajo,
    }


def get_chart_data(db: Session, fd_dt: datetime, fh_dt: datetime, fh: date):
    """Datos para todas las gráficas Chart.js del dashboard."""
    V = models.Venta
    DV = models.DetalleVenta
    MI = models.MovimientoInventario

    inicio_7d = fh - timedelta(days=6)

    # Top 5 productos más vendidos
    top_productos = db.query(
        DV.producto_nombre,
        func.sum(DV.cantidad).label("total_qty"),
        func.sum(DV.subtotal).label("total_revenue"),
    ).join(V).filter(
        V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
    ).group_by(DV.producto_nombre).order_by(
        func.sum(DV.cantidad).desc()
    ).limit(5).all()

    # Ventas últimos 7 días
    ventas_7d_raw = dict(
        db.query(cast(V.fecha, Date), func.sum(V.total)).filter(
            cast(V.fecha, Date) >= inicio_7d,
            cast(V.fecha, Date) <= fh,
            V.estado == "COMPLETADA",
        ).group_by(cast(V.fecha, Date)).all()
    )
    ventas_7d = [
        round(float(ventas_7d_raw.get(fh - timedelta(days=i), 0)), 2)
        for i in range(6, -1, -1)
    ]

    # Movimientos últimos 7 días
    mov_7d_raw = db.query(
        cast(MI.fecha, Date), MI.tipo, func.count(MI.id),
    ).filter(
        cast(MI.fecha, Date) >= inicio_7d,
        cast(MI.fecha, Date) <= fh,
    ).group_by(cast(MI.fecha, Date), MI.tipo).all()

    mov_dict = {}
    for fecha_mov, tipo_mov, cnt in mov_7d_raw:
        mov_dict[(fecha_mov, tipo_mov)] = cnt  # pragma: no cover — SQLite cast(Date) returns empty

    labels_7d, entradas_7d, salidas_7d = [], [], []
    for i in range(6, -1, -1):
        dia = fh - timedelta(days=i)
        labels_7d.append(dia.strftime("%d/%m"))
        entradas_7d.append(mov_dict.get((dia, "ENTRADA"), 0))
        salidas_7d.append(mov_dict.get((dia, "SALIDA"), 0))

    # Valor inventario por categoría
    cats_raw = db.query(
        models.Categoria.nombre,
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).join(models.Producto, models.Producto.categoria_id == models.Categoria.id).filter(
        models.Producto.activo == True
    ).group_by(models.Categoria.nombre).all()

    sin_cat = db.query(
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).filter(
        models.Producto.activo == True, models.Producto.categoria_id == None
    ).scalar() or 0.0

    cat_labels = [c[0] for c in cats_raw]
    cat_valores = [round(float(c[1] or 0), 2) for c in cats_raw]
    if sin_cat > 0:
        cat_labels.append("Sin categoría")
        cat_valores.append(round(float(sin_cat), 2))

    # Estado deudas y facturas (doughnut)
    estados_deuda = {"PENDIENTE": 0, "PARCIAL": 0, "PAGADO": 0}
    for row in db.query(models.Deuda.estado, func.count(models.Deuda.id)).group_by(models.Deuda.estado).all():
        if row[0] in estados_deuda:
            estados_deuda[row[0]] = row[1]

    estados_factura = {"PENDIENTE": 0, "PARCIAL": 0, "PAGADO": 0}
    for row in db.query(models.Factura.estado, func.count(models.Factura.id)).group_by(models.Factura.estado).all():
        if row[0] in estados_factura:
            estados_factura[row[0]] = row[1]

    return {
        "top_productos": top_productos,
        "chart_ventas_7d": json.dumps(ventas_7d),
        "chart_labels_7d": json.dumps(labels_7d),
        "chart_entradas_7d": json.dumps(entradas_7d),
        "chart_salidas_7d": json.dumps(salidas_7d),
        "chart_cat_labels": json.dumps(cat_labels),
        "chart_cat_valores": json.dumps(cat_valores),
        "chart_deudas": json.dumps(list(estados_deuda.values())),
        "chart_facturas": json.dumps(list(estados_factura.values())),
    }
