"""Dashboard consolidado para SUPERADMIN — métricas de todos los locales."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta

from database import get_db
from templates_config import templates
from auth import require_superadmin
import models

router = APIRouter(prefix="/super", tags=["super_dashboard"])


@router.get("")
def super_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    locales = db.query(models.Local).order_by(models.Local.activo.desc(), models.Local.nombre).all()
    hoy = date.today()
    inicio_mes = datetime(hoy.year, hoy.month, 1)
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    fin_hoy = datetime.combine(hoy, datetime.max.time())

    # Métricas globales
    total_locales = len(locales)
    locales_activos = sum(1 for l in locales if l.activo)
    total_usuarios = db.query(func.count(models.Usuario.id)).filter(models.Usuario.activo == True).scalar() or 0
    total_productos = db.query(func.count(models.Producto.id)).filter(models.Producto.activo == True).scalar() or 0

    ventas_mes_total = db.query(func.sum(models.Venta.total)).filter(
        models.Venta.fecha >= inicio_mes, models.Venta.fecha <= fin_hoy,
        models.Venta.estado == "COMPLETADA"
    ).scalar() or 0.0

    ventas_hoy_total = db.query(func.sum(models.Venta.total)).filter(
        models.Venta.fecha >= inicio_hoy,
        models.Venta.fecha <= fin_hoy,
        models.Venta.estado == "COMPLETADA"
    ).scalar() or 0.0

    # Métricas por local — queries agrupadas en vez de N+1
    usuarios_por_local = dict(
        db.query(models.Usuario.local_id, func.count(models.Usuario.id))
        .filter(models.Usuario.activo == True)
        .group_by(models.Usuario.local_id).all()
    )
    productos_por_local = dict(
        db.query(models.Producto.local_id, func.count(models.Producto.id))
        .filter(models.Producto.activo == True)
        .group_by(models.Producto.local_id).all()
    )
    ventas_mes_por_local = dict(
        db.query(models.Venta.local_id, func.sum(models.Venta.total))
        .filter(
            models.Venta.fecha >= inicio_mes, models.Venta.fecha <= fin_hoy,
            models.Venta.estado == "COMPLETADA"
        ).group_by(models.Venta.local_id).all()
    )
    ventas_hoy_por_local = dict(
        db.query(models.Venta.local_id, func.sum(models.Venta.total))
        .filter(
            models.Venta.fecha >= inicio_hoy, models.Venta.fecha <= fin_hoy,
            models.Venta.estado == "COMPLETADA"
        ).group_by(models.Venta.local_id).all()
    )
    stock_bajo_por_local = dict(
        db.query(models.Producto.local_id, func.count(models.Producto.id))
        .filter(
            models.Producto.activo == True,
            models.Producto.stock_actual <= models.Producto.stock_minimo
        ).group_by(models.Producto.local_id).all()
    )
    deudas_por_local = dict(
        db.query(
            models.Deuda.local_id,
            func.sum(models.Deuda.monto_total - models.Deuda.monto_pagado)
        ).filter(
            models.Deuda.estado.in_(["PENDIENTE", "PARCIAL"])
        ).group_by(models.Deuda.local_id).all()
    )

    local_stats = []
    for local in locales:
        lid = local.id
        local_stats.append({
            "local": local,
            "usuarios": usuarios_por_local.get(lid, 0),
            "productos": productos_por_local.get(lid, 0),
            "ventas_mes": ventas_mes_por_local.get(lid, 0) or 0.0,
            "ventas_hoy": ventas_hoy_por_local.get(lid, 0) or 0.0,
            "stock_bajo": stock_bajo_por_local.get(lid, 0),
            "deudas_pendientes": deudas_por_local.get(lid, 0) or 0.0,
        })

    return templates.TemplateResponse("super/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "total_locales": total_locales,
        "locales_activos": locales_activos,
        "total_usuarios": total_usuarios,
        "total_productos": total_productos,
        "ventas_mes_total": ventas_mes_total,
        "ventas_hoy_total": ventas_hoy_total,
        "local_stats": local_stats,
        "fecha_hoy": hoy.strftime("%d de %B de %Y"),
    })
