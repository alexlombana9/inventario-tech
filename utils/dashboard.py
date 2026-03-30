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


def _apply_local_filter(query, model, local_id):
    """Aplica filtro de local_id a un query si local_id no es None."""
    if local_id is not None:
        return query.filter(model.local_id == local_id)
    return query


def get_general_metrics(db: Session, fd_dt: datetime = None, fh_dt: datetime = None, local_id: int = None):
    """Métricas generales. Cuando se pasan fechas, muestra datos del período."""
    P = models.Producto
    V = models.Venta
    DV = models.DetalleVenta

    # Estas métricas son siempre estado actual
    q_stock = db.query(func.count(P.id)).filter(P.activo == True, P.stock_actual <= P.stock_minimo)
    q_valor = db.query(func.sum(P.stock_actual * P.precio_costo)).filter(P.activo == True)

    if local_id is not None:
        q_stock = q_stock.filter(P.local_id == local_id)
        q_valor = q_valor.filter(P.local_id == local_id)

    stock_bajo = q_stock.scalar() or 0
    valor_inventario = q_valor.scalar() or 0.0

    # Productos vendidos en el período
    productos_vendidos = 0
    clientes_periodo = 0
    if fd_dt and fh_dt:
        q_pv = db.query(func.count(func.distinct(DV.producto_id))).join(V).filter(
            V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
        )
        q_cli = db.query(func.count(func.distinct(V.cliente_id))).filter(
            V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA",
            V.cliente_id != None,
        )
        if local_id is not None:
            q_pv = q_pv.filter(V.local_id == local_id)
            q_cli = q_cli.filter(V.local_id == local_id)
        productos_vendidos = q_pv.scalar() or 0
        clientes_periodo = q_cli.scalar() or 0

    # Totales activos (siempre estado actual)
    q_total_prod = db.query(func.count(P.id)).filter(P.activo == True)
    q_total_cli = db.query(func.count(models.Cliente.id)).filter(models.Cliente.activo == True)
    q_total_prov = db.query(func.count(models.Proveedor.id)).filter(models.Proveedor.activo == True)
    q_total_cat = db.query(func.count(models.Categoria.id)).filter(models.Categoria.activo == True)
    if local_id is not None:
        q_total_prod = q_total_prod.filter(P.local_id == local_id)
        q_total_cli = q_total_cli.filter(models.Cliente.local_id == local_id)
        q_total_prov = q_total_prov.filter(models.Proveedor.local_id == local_id)
        q_total_cat = q_total_cat.filter(models.Categoria.local_id == local_id)

    return {
        "total_productos": q_total_prod.scalar() or 0,
        "total_clientes": q_total_cli.scalar() or 0,
        "total_proveedores": q_total_prov.scalar() or 0,
        "total_categorias": q_total_cat.scalar() or 0,
        "productos_vendidos": productos_vendidos,
        "clientes_periodo": clientes_periodo,
        "stock_bajo": stock_bajo,
        "valor_inventario": valor_inventario,
    }


def get_period_metrics(db: Session, fd_dt: datetime, fh_dt: datetime, local_id: int = None):
    """Métricas de ventas y movimientos filtradas por período."""
    V = models.Venta
    DV = models.DetalleVenta
    MI = models.MovimientoInventario

    q_mov = db.query(func.count(MI.id)).filter(MI.fecha >= fd_dt, MI.fecha <= fh_dt)
    q_ven = db.query(func.sum(V.total)).filter(V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA")
    q_num = db.query(func.count(V.id)).filter(V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA")
    q_gan = db.query(func.sum(DV.subtotal - DV.precio_costo * DV.cantidad)).join(V).filter(
        V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
    )
    G = models.Gasto
    q_gas = db.query(func.sum(G.monto)).filter(
        G.activo == True, G.fecha >= fd_dt, G.fecha <= fh_dt
    )

    if local_id is not None:
        q_mov = q_mov.filter(MI.local_id == local_id)
        q_ven = q_ven.filter(V.local_id == local_id)
        q_num = q_num.filter(V.local_id == local_id)
        q_gan = q_gan.filter(V.local_id == local_id)
        q_gas = q_gas.filter(G.local_id == local_id)

    movimientos_periodo = q_mov.scalar() or 0
    ventas_periodo = q_ven.scalar() or 0.0
    num_ventas_periodo = q_num.scalar() or 0
    ganancia_periodo = q_gan.scalar() or 0.0
    gastos_periodo = q_gas.scalar() or 0.0

    return {
        "movimientos_periodo": movimientos_periodo,
        "ventas_periodo": ventas_periodo,
        "num_ventas_periodo": num_ventas_periodo,
        "ganancia_periodo": round(ganancia_periodo, 2),
        "gastos_periodo": round(gastos_periodo, 2),
    }


def get_financial_metrics(db: Session, fd_dt: datetime = None, fh_dt: datetime = None, local_id: int = None):
    """Métricas financieras filtradas por período."""
    # Deudas creadas en el período
    q_deudas = db.query(
        func.sum(models.Deuda.monto_total - models.Deuda.monto_pagado)
    ).filter(models.Deuda.estado.in_(["PENDIENTE", "PARCIAL"]))

    q_dv = db.query(func.count(models.Deuda.id)).filter(
        models.Deuda.estado.in_(["PENDIENTE", "PARCIAL"]),
        models.Deuda.fecha_vencimiento != None,
        models.Deuda.fecha_vencimiento < datetime.now()
    )

    q_fact = db.query(
        func.sum(models.Factura.monto_total - models.Factura.monto_cobrado)
    ).filter(models.Factura.estado.in_(["PENDIENTE", "PARCIAL"]))

    q_fv = db.query(func.count(models.Factura.id)).filter(
        models.Factura.estado.in_(["PENDIENTE", "PARCIAL"]),
        models.Factura.fecha_vencimiento != None,
        models.Factura.fecha_vencimiento < datetime.now()
    )

    # Filtrar por período
    if fd_dt and fh_dt:
        q_deudas = q_deudas.filter(models.Deuda.fecha_deuda >= fd_dt, models.Deuda.fecha_deuda <= fh_dt)
        q_dv = q_dv.filter(models.Deuda.fecha_deuda >= fd_dt, models.Deuda.fecha_deuda <= fh_dt)
        q_fact = q_fact.filter(models.Factura.fecha_emision >= fd_dt, models.Factura.fecha_emision <= fh_dt)
        q_fv = q_fv.filter(models.Factura.fecha_emision >= fd_dt, models.Factura.fecha_emision <= fh_dt)

    if local_id is not None:
        q_deudas = q_deudas.filter(models.Deuda.local_id == local_id)
        q_dv = q_dv.filter(models.Deuda.local_id == local_id)
        q_fact = q_fact.filter(models.Factura.local_id == local_id)
        q_fv = q_fv.filter(models.Factura.local_id == local_id)

    deudas_pendientes_total = q_deudas.scalar() or 0.0
    deudas_vencidas_count = q_dv.scalar() or 0
    facturas_por_cobrar_total = q_fact.scalar() or 0.0
    facturas_vencidas_count = q_fv.scalar() or 0

    return {
        "deudas_pendientes_total": deudas_pendientes_total,
        "deudas_vencidas_count": deudas_vencidas_count,
        "facturas_por_cobrar_total": facturas_por_cobrar_total,
        "facturas_vencidas_count": facturas_vencidas_count,
    }


def get_tables_data(db: Session, fd_dt: datetime = None, fh_dt: datetime = None, local_id: int = None):
    """Datos para tablas: movimientos del período y productos con stock bajo."""
    q_mov = db.query(models.MovimientoInventario).options(
        joinedload(models.MovimientoInventario.producto)
    )
    if fd_dt is not None and fh_dt is not None:
        q_mov = q_mov.filter(
            models.MovimientoInventario.fecha >= fd_dt,
            models.MovimientoInventario.fecha <= fh_dt,
        )
    q_stock = db.query(models.Producto).options(
        joinedload(models.Producto.categoria)
    ).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual <= models.Producto.stock_minimo
    )

    if local_id is not None:
        q_mov = q_mov.filter(models.MovimientoInventario.local_id == local_id)
        q_stock = q_stock.filter(models.Producto.local_id == local_id)

    ultimos_movimientos = q_mov.order_by(
        models.MovimientoInventario.fecha.desc()
    ).limit(10).all()

    productos_stock_bajo = q_stock.order_by(
        models.Producto.stock_actual.asc()
    ).limit(5).all()

    return {
        "ultimos_movimientos": ultimos_movimientos,
        "productos_stock_bajo": productos_stock_bajo,
    }


def _build_period_buckets(fd: date, fh: date):
    """Genera buckets de fechas para las graficas segun el rango seleccionado.

    <= 31 dias: diario (dd/mm)
    <= 90 dias: semanal (dd/mm)
    > 90 dias: mensual (mmm yy)
    """
    total_days = (fh - fd).days + 1

    if total_days <= 31:
        # Diario
        buckets = []
        for i in range(total_days):
            d = fd + timedelta(days=i)
            buckets.append((d, d, d.strftime("%d/%m")))
        return buckets

    if total_days <= 90:
        # Semanal (lunes a domingo)
        buckets = []
        current = fd
        while current <= fh:
            week_end = min(current + timedelta(days=6), fh)
            label = f"{current.strftime('%d/%m')}"
            buckets.append((current, week_end, label))
            current = week_end + timedelta(days=1)
        return buckets

    # Mensual
    buckets = []
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    current = fd.replace(day=1)
    while current <= fh:
        month_end = (current + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        bucket_start = max(current, fd)
        bucket_end = min(month_end, fh)
        label = f"{meses_es[current.month - 1]} {current.strftime('%y')}"
        buckets.append((bucket_start, bucket_end, label))
        current = (current + timedelta(days=32)).replace(day=1)
    return buckets


def get_chart_data(db: Session, fd_dt: datetime, fh_dt: datetime, fh: date, local_id: int = None):
    """Datos para todas las graficas Chart.js del dashboard."""
    V = models.Venta
    DV = models.DetalleVenta
    MI = models.MovimientoInventario
    fd = fd_dt.date()

    buckets = _build_period_buckets(fd, fh)

    # Top 5 productos mas vendidos (rango completo)
    q_top = db.query(
        DV.producto_nombre,
        func.sum(DV.cantidad).label("total_qty"),
        func.sum(DV.subtotal).label("total_revenue"),
    ).join(V).filter(
        V.fecha >= fd_dt, V.fecha <= fh_dt, V.estado == "COMPLETADA"
    )
    if local_id is not None:
        q_top = q_top.filter(V.local_id == local_id)
    top_productos = q_top.group_by(DV.producto_nombre).order_by(
        func.sum(DV.cantidad).desc()
    ).limit(5).all()

    # Ventas por dia en el rango completo
    q_ventas = db.query(cast(V.fecha, Date), func.sum(V.total)).filter(
        cast(V.fecha, Date) >= fd,
        cast(V.fecha, Date) <= fh,
        V.estado == "COMPLETADA",
    )
    if local_id is not None:
        q_ventas = q_ventas.filter(V.local_id == local_id)
    ventas_raw = dict(q_ventas.group_by(cast(V.fecha, Date)).all())

    # Movimientos por dia en el rango completo
    q_mov = db.query(
        cast(MI.fecha, Date), MI.tipo, func.count(MI.id),
    ).filter(
        cast(MI.fecha, Date) >= fd,
        cast(MI.fecha, Date) <= fh,
    )
    if local_id is not None:
        q_mov = q_mov.filter(MI.local_id == local_id)
    mov_raw = q_mov.group_by(cast(MI.fecha, Date), MI.tipo).all()

    mov_dict = {}
    for fecha_mov, tipo_mov, cnt in mov_raw:
        mov_dict[(fecha_mov, tipo_mov)] = cnt  # pragma: no cover — SQLite cast(Date) returns empty

    # Agregar datos por bucket
    labels_period = []
    ventas_period = []
    entradas_period = []
    salidas_period = []

    for bucket_start, bucket_end, label in buckets:
        labels_period.append(label)
        v_sum = 0.0
        e_sum = 0
        s_sum = 0
        d = bucket_start
        while d <= bucket_end:
            v_sum += float(ventas_raw.get(d, 0) or 0)
            e_sum += mov_dict.get((d, "ENTRADA"), 0)
            s_sum += mov_dict.get((d, "SALIDA"), 0)
            d += timedelta(days=1)
        ventas_period.append(round(v_sum, 2))
        entradas_period.append(e_sum)
        salidas_period.append(s_sum)

    # Valor inventario por categoria (estado actual, no filtra por fecha)
    q_cats = db.query(
        models.Categoria.nombre,
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).join(models.Producto, models.Producto.categoria_id == models.Categoria.id).filter(
        models.Producto.activo == True
    )
    q_sincat = db.query(
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).filter(
        models.Producto.activo == True, models.Producto.categoria_id == None
    )
    if local_id is not None:
        q_cats = q_cats.filter(models.Producto.local_id == local_id)
        q_sincat = q_sincat.filter(models.Producto.local_id == local_id)

    cats_raw = q_cats.group_by(models.Categoria.nombre).all()
    sin_cat = q_sincat.scalar() or 0.0

    cat_labels = [c[0] for c in cats_raw]
    cat_valores = [round(float(c[1] or 0), 2) for c in cats_raw]
    if sin_cat > 0:
        cat_labels.append("Sin categoria")
        cat_valores.append(round(float(sin_cat), 2))

    # Estado deudas y facturas (estado actual)
    q_ed = db.query(models.Deuda.estado, func.count(models.Deuda.id))
    q_ef = db.query(models.Factura.estado, func.count(models.Factura.id))
    if local_id is not None:
        q_ed = q_ed.filter(models.Deuda.local_id == local_id)
        q_ef = q_ef.filter(models.Factura.local_id == local_id)

    estados_deuda = {"PENDIENTE": 0, "PARCIAL": 0, "PAGADO": 0}
    for row in q_ed.group_by(models.Deuda.estado).all():
        if row[0] in estados_deuda:
            estados_deuda[row[0]] = row[1]

    estados_factura = {"PENDIENTE": 0, "PARCIAL": 0, "PAGADO": 0}
    for row in q_ef.group_by(models.Factura.estado).all():
        if row[0] in estados_factura:
            estados_factura[row[0]] = row[1]

    return {
        "top_productos": top_productos,
        "chart_ventas_7d": json.dumps(ventas_period),
        "chart_labels_7d": json.dumps(labels_period),
        "chart_entradas_7d": json.dumps(entradas_period),
        "chart_salidas_7d": json.dumps(salidas_period),
        "chart_cat_labels": json.dumps(cat_labels),
        "chart_cat_valores": json.dumps(cat_valores),
        "chart_deudas": json.dumps(list(estados_deuda.values())),
        "chart_facturas": json.dumps(list(estados_factura.values())),
    }
