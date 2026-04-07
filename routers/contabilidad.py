"""
Modulo de Contabilidad Financiera para TechStock.
Dashboard que agrega datos financieros de modulos existentes
para mostrar el estado contable en tiempo real de cada local.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from datetime import datetime, date, timedelta

from database import get_db
from templates_config import templates
from auth import require_permiso, get_local_id
import models

router = APIRouter(prefix="/contabilidad", tags=["Contabilidad"])


def _parse_fechas(fecha_desde: str = None, fecha_hasta: str = None):
    """Parsea fechas de filtro. Default: mes actual."""
    hoy = date.today()
    if not fecha_desde:
        fd = date(hoy.year, hoy.month, 1)
    else:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        except ValueError:
            fd = date(hoy.year, hoy.month, 1)

    if not fecha_hasta:
        fh = hoy
    else:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        except ValueError:
            fh = hoy

    fd_dt = datetime(fd.year, fd.month, fd.day, 0, 0, 0)
    fh_dt = datetime(fh.year, fh.month, fh.day, 23, 59, 59)
    return fd, fh, fd_dt, fh_dt


def _local_filter(query, model, local_id):
    """Aplica filtro de local_id si no es None."""
    if local_id is not None:
        return query.filter(model.local_id == local_id)
    return query


# ── Dashboard principal ──────────────────────────────────────

@router.get("")
def contabilidad_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(require_permiso("contabilidad")),
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    local_id = get_local_id(request)
    fd, fh, fd_dt, fh_dt = _parse_fechas(fecha_desde, fecha_hasta)
    hoy_dt = datetime.now()

    # ── 1. INGRESOS (ventas completadas en el periodo) ──
    ventas_q = db.query(
        func.coalesce(func.sum(models.Venta.total), 0),
        func.count(models.Venta.id),
    ).filter(
        models.Venta.estado == "COMPLETADA",
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
    )
    ventas_q = _local_filter(ventas_q, models.Venta, local_id)
    total_ventas, cantidad_ventas = ventas_q.one()

    # Costo de ventas (suma de precio_costo * cantidad de detalles)
    costo_q = db.query(
        func.coalesce(func.sum(models.DetalleVenta.precio_costo * models.DetalleVenta.cantidad), 0)
    ).join(
        models.Venta, models.DetalleVenta.venta_id == models.Venta.id
    ).filter(
        models.Venta.estado == "COMPLETADA",
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
    )
    costo_q = _local_filter(costo_q, models.Venta, local_id)
    costo_ventas = costo_q.scalar() or 0

    ganancia_bruta = total_ventas - costo_ventas

    # ── 2. EGRESOS (gastos activos en el periodo) ──
    gastos_base = db.query(models.Gasto).filter(
        models.Gasto.activo == True,
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    )
    gastos_base = _local_filter(gastos_base, models.Gasto, local_id)

    total_gastos_q = db.query(
        func.coalesce(func.sum(models.Gasto.monto), 0)
    ).filter(
        models.Gasto.activo == True,
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    )
    total_gastos_q = _local_filter(total_gastos_q, models.Gasto, local_id)
    total_gastos = total_gastos_q.scalar() or 0

    gastos_dir_q = db.query(
        func.coalesce(func.sum(models.Gasto.monto), 0)
    ).filter(
        models.Gasto.activo == True,
        models.Gasto.tipo == "DIRECTO",
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    )
    gastos_dir_q = _local_filter(gastos_dir_q, models.Gasto, local_id)
    gastos_directos = gastos_dir_q.scalar() or 0

    gastos_indir_q = db.query(
        func.coalesce(func.sum(models.Gasto.monto), 0)
    ).filter(
        models.Gasto.activo == True,
        models.Gasto.tipo == "INDIRECTO",
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    )
    gastos_indir_q = _local_filter(gastos_indir_q, models.Gasto, local_id)
    gastos_indirectos = gastos_indir_q.scalar() or 0

    # Gastos por categoria
    gastos_cat_q = db.query(
        models.Gasto.categoria_gasto,
        models.Gasto.tipo,
        func.sum(models.Gasto.monto),
    ).filter(
        models.Gasto.activo == True,
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    ).group_by(
        models.Gasto.categoria_gasto, models.Gasto.tipo,
    ).order_by(func.sum(models.Gasto.monto).desc())
    gastos_cat_q = _local_filter(gastos_cat_q, models.Gasto, local_id)
    gastos_por_categoria = []
    for cat, tipo, monto in gastos_cat_q.all():
        gastos_por_categoria.append({
            "categoria": cat or "Sin categoria",
            "tipo": tipo,
            "total": monto or 0,
            "porcentaje": round((monto / total_gastos * 100), 1) if total_gastos > 0 else 0,
        })

    # ── 3. UTILIDAD ──
    utilidad_neta = ganancia_bruta - total_gastos
    margen_bruto = round((ganancia_bruta / total_ventas * 100), 1) if total_ventas > 0 else 0
    margen_neto = round((utilidad_neta / total_ventas * 100), 1) if total_ventas > 0 else 0

    # ── 4. CUENTAS POR COBRAR (facturas) ──
    fact_pend_q = db.query(
        func.coalesce(func.sum(models.Factura.monto_total - models.Factura.monto_cobrado), 0),
        func.count(models.Factura.id),
    ).filter(
        models.Factura.estado.in_(["PENDIENTE", "PARCIAL"]),
    )
    fact_pend_q = _local_filter(fact_pend_q, models.Factura, local_id)
    facturas_pendientes_monto, facturas_pendientes_count = fact_pend_q.one()

    fact_venc_q = db.query(
        func.coalesce(func.sum(models.Factura.monto_total - models.Factura.monto_cobrado), 0),
        func.count(models.Factura.id),
    ).filter(
        models.Factura.estado.in_(["PENDIENTE", "PARCIAL"]),
        models.Factura.fecha_vencimiento < hoy_dt,
        models.Factura.fecha_vencimiento.isnot(None),
    )
    fact_venc_q = _local_filter(fact_venc_q, models.Factura, local_id)
    facturas_vencidas_monto, facturas_vencidas_count = fact_venc_q.one()

    cobrado_periodo_q = db.query(
        func.coalesce(func.sum(models.PagoFactura.monto), 0)
    ).filter(
        models.PagoFactura.fecha_cobro >= fd_dt,
        models.PagoFactura.fecha_cobro <= fh_dt,
    )
    cobrado_periodo_q = _local_filter(cobrado_periodo_q, models.PagoFactura, local_id)
    total_cobrado_periodo = cobrado_periodo_q.scalar() or 0

    # ── 5. CUENTAS POR PAGAR (deudas) ──
    deud_pend_q = db.query(
        func.coalesce(func.sum(models.Deuda.monto_total - models.Deuda.monto_pagado), 0),
        func.count(models.Deuda.id),
    ).filter(
        models.Deuda.estado.in_(["PENDIENTE", "PARCIAL"]),
    )
    deud_pend_q = _local_filter(deud_pend_q, models.Deuda, local_id)
    deudas_pendientes_monto, deudas_pendientes_count = deud_pend_q.one()

    deud_venc_q = db.query(
        func.coalesce(func.sum(models.Deuda.monto_total - models.Deuda.monto_pagado), 0),
        func.count(models.Deuda.id),
    ).filter(
        models.Deuda.estado.in_(["PENDIENTE", "PARCIAL"]),
        models.Deuda.fecha_vencimiento < hoy_dt,
        models.Deuda.fecha_vencimiento.isnot(None),
    )
    deud_venc_q = _local_filter(deud_venc_q, models.Deuda, local_id)
    deudas_vencidas_monto, deudas_vencidas_count = deud_venc_q.one()

    pagado_periodo_q = db.query(
        func.coalesce(func.sum(models.PagoDeuda.monto), 0)
    ).filter(
        models.PagoDeuda.fecha_pago >= fd_dt,
        models.PagoDeuda.fecha_pago <= fh_dt,
    )
    pagado_periodo_q = _local_filter(pagado_periodo_q, models.PagoDeuda, local_id)
    total_pagado_periodo = pagado_periodo_q.scalar() or 0

    # ── 6. BALANCE SIMPLIFICADO ──
    valor_inv_q = db.query(
        func.coalesce(func.sum(models.Producto.stock_actual * models.Producto.precio_costo), 0)
    ).filter(models.Producto.activo == True)
    valor_inv_q = _local_filter(valor_inv_q, models.Producto, local_id)
    valor_inventario = valor_inv_q.scalar() or 0

    # Efectivo en caja abierta
    caja_q = db.query(models.Caja).filter(models.Caja.estado == "ABIERTA")
    caja_q = _local_filter(caja_q, models.Caja, local_id)
    cajas_abiertas = caja_q.all()
    efectivo_caja = sum(c.saldo_esperado for c in cajas_abiertas)

    activos = valor_inventario + facturas_pendientes_monto + efectivo_caja
    pasivos = deudas_pendientes_monto
    patrimonio_estimado = activos - pasivos

    # ── Periodo label ──
    periodo_label = f"{fd.strftime('%d/%m/%Y')} - {fh.strftime('%d/%m/%Y')}"

    ctx = {
        "request": request,
        # Filtros
        "fecha_desde": fd.strftime("%Y-%m-%d"),
        "fecha_hasta": fh.strftime("%Y-%m-%d"),
        "periodo_label": periodo_label,
        # Ingresos
        "total_ventas": total_ventas,
        "cantidad_ventas": cantidad_ventas,
        "costo_ventas": costo_ventas,
        "ganancia_bruta": ganancia_bruta,
        # Egresos
        "total_gastos": total_gastos,
        "gastos_directos": gastos_directos,
        "gastos_indirectos": gastos_indirectos,
        "gastos_por_categoria": gastos_por_categoria,
        # Utilidad
        "utilidad_neta": utilidad_neta,
        "margen_bruto": margen_bruto,
        "margen_neto": margen_neto,
        # Cuentas por cobrar
        "facturas_pendientes_monto": facturas_pendientes_monto,
        "facturas_pendientes_count": facturas_pendientes_count,
        "facturas_vencidas_monto": facturas_vencidas_monto,
        "facturas_vencidas_count": facturas_vencidas_count,
        "total_cobrado_periodo": total_cobrado_periodo,
        # Cuentas por pagar
        "deudas_pendientes_monto": deudas_pendientes_monto,
        "deudas_pendientes_count": deudas_pendientes_count,
        "deudas_vencidas_monto": deudas_vencidas_monto,
        "deudas_vencidas_count": deudas_vencidas_count,
        "total_pagado_periodo": total_pagado_periodo,
        # Balance
        "valor_inventario": valor_inventario,
        "efectivo_caja": efectivo_caja,
        "activos": activos,
        "pasivos": pasivos,
        "patrimonio_estimado": patrimonio_estimado,
    }

    return templates.TemplateResponse("contabilidad/index.html", ctx)


# ── API: Flujo de caja por dia ───────────────────────────────

@router.get("/api/flujo")
def api_flujo_caja(
    request: Request,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(require_permiso("contabilidad")),
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    local_id = get_local_id(request)
    fd, fh, fd_dt, fh_dt = _parse_fechas(fecha_desde, fecha_hasta)

    # Generar lista de dias en el rango
    dias = []
    labels = []
    current = fd
    while current <= fh:
        dias.append(current)
        labels.append(current.strftime("%d/%m"))
        current += timedelta(days=1)

    # Ingresos por dia (ventas completadas)
    ingresos_raw = db.query(
        func.date(models.Venta.fecha),
        func.coalesce(func.sum(models.Venta.total), 0),
    ).filter(
        models.Venta.estado == "COMPLETADA",
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
    ).group_by(func.date(models.Venta.fecha))
    ingresos_raw = _local_filter(ingresos_raw, models.Venta, local_id)
    ingresos_map = {}
    for fecha_row, monto in ingresos_raw.all():
        if fecha_row:
            key = fecha_row if isinstance(fecha_row, date) else fecha_row
            ingresos_map[str(key)] = float(monto)

    # Egresos por dia (gastos)
    egresos_gastos = db.query(
        func.date(models.Gasto.fecha),
        func.coalesce(func.sum(models.Gasto.monto), 0),
    ).filter(
        models.Gasto.activo == True,
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    ).group_by(func.date(models.Gasto.fecha))
    egresos_gastos = _local_filter(egresos_gastos, models.Gasto, local_id)
    egresos_gastos_map = {}
    for fecha_row, monto in egresos_gastos.all():
        if fecha_row:
            key = fecha_row if isinstance(fecha_row, date) else fecha_row
            egresos_gastos_map[str(key)] = float(monto)

    # Egresos por dia (pagos de deudas)
    egresos_pagos = db.query(
        func.date(models.PagoDeuda.fecha_pago),
        func.coalesce(func.sum(models.PagoDeuda.monto), 0),
    ).filter(
        models.PagoDeuda.fecha_pago >= fd_dt,
        models.PagoDeuda.fecha_pago <= fh_dt,
    ).group_by(func.date(models.PagoDeuda.fecha_pago))
    egresos_pagos = _local_filter(egresos_pagos, models.PagoDeuda, local_id)
    egresos_pagos_map = {}
    for fecha_row, monto in egresos_pagos.all():
        if fecha_row:
            key = fecha_row if isinstance(fecha_row, date) else fecha_row
            egresos_pagos_map[str(key)] = float(monto)

    # Construir arrays
    ingresos = []
    egresos = []
    for d in dias:
        ds = str(d)
        ingresos.append(ingresos_map.get(ds, 0))
        egreso_dia = egresos_gastos_map.get(ds, 0) + egresos_pagos_map.get(ds, 0)
        egresos.append(egreso_dia)

    return JSONResponse({
        "labels": labels,
        "ingresos": ingresos,
        "egresos": egresos,
    })


# ── API: Gastos por categoria ────────────────────────────────

@router.get("/api/gastos-categoria")
def api_gastos_categoria(
    request: Request,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(require_permiso("contabilidad")),
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    local_id = get_local_id(request)
    fd, fh, fd_dt, fh_dt = _parse_fechas(fecha_desde, fecha_hasta)

    gastos_cat_q = db.query(
        models.Gasto.categoria_gasto,
        func.sum(models.Gasto.monto),
    ).filter(
        models.Gasto.activo == True,
        models.Gasto.fecha >= fd_dt,
        models.Gasto.fecha <= fh_dt,
    ).group_by(
        models.Gasto.categoria_gasto,
    ).order_by(func.sum(models.Gasto.monto).desc())
    gastos_cat_q = _local_filter(gastos_cat_q, models.Gasto, local_id)

    labels = []
    valores = []
    for cat, monto in gastos_cat_q.all():
        labels.append(cat or "Sin categoria")
        valores.append(float(monto or 0))

    return JSONResponse({
        "labels": labels,
        "valores": valores,
    })
