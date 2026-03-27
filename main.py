import os
import sys
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date, extract
from datetime import datetime, date, timedelta
import uvicorn
import socket
import json

# ── Logging estructurado ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("techstock")

from database import engine, Base, get_db
from templates_config import templates
from middleware import AuthMiddleware
from auth import get_flash, user_has_permiso
import models

# ── Crear tablas y ejecutar migraciones (solo en producción) ──
if os.environ.get("TESTING") != "1":
    Base.metadata.create_all(bind=engine)

    from migrations import run_migrations
    run_migrations(engine)

    from seed import run_seed
    from database import SessionLocal
    _seed_db = SessionLocal()
    try:
        run_seed(_seed_db)
    finally:
        _seed_db.close()

# ── App ──
app = FastAPI(title="TechStock - Sistema de Inventario")
app.add_middleware(AuthMiddleware)
_static_dir = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__)),
    "static"
)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# ── Routers ──
from routers import productos, categorias, proveedores, inventario, reportes, deudas, facturas, acreedores, gastos
from routers import auth_router, usuarios, configuracion, clientes, ventas, caja, backup, importar, perfil, auditoria

app.include_router(auth_router.router)
app.include_router(usuarios.router)
app.include_router(configuracion.router)
app.include_router(clientes.router)
app.include_router(ventas.router)
app.include_router(caja.router)
app.include_router(backup.router)
app.include_router(importar.router)
app.include_router(perfil.router)
app.include_router(auditoria.router)
app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(proveedores.router)
app.include_router(inventario.router)
app.include_router(reportes.router)
app.include_router(deudas.router)
app.include_router(facturas.router)
app.include_router(acreedores.router)
app.include_router(gastos.router)


def _base_context(request: Request) -> dict:
    """Contexto base que incluye usuario actual y flash messages."""
    flash = get_flash(request)
    return {
        "request": request,
        "current_user": getattr(request.state, "user", None),
        "flash": flash,
    }


@app.get("/guia")
def guia(request: Request):
    ctx = _base_context(request)
    return templates.TemplateResponse("guia/index.html", ctx)


@app.get("/legal")
def legal(request: Request):
    ctx = _base_context(request)
    return templates.TemplateResponse("legal/index.html", ctx)


@app.get("/")
def index(
    request: Request,
    db: Session = Depends(get_db),
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    hoy = date.today()
    ctx = _base_context(request)

    # ── Filtro temporal global ─────────────────────────────────
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

    # ── Métricas generales ─────────────────────────────────────
    total_productos   = db.query(models.Producto).filter(models.Producto.activo == True).count()
    total_proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).count()
    total_categorias  = db.query(models.Categoria).count()

    stock_bajo = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual <= models.Producto.stock_minimo
    ).count()

    valor_inventario = db.query(
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).filter(models.Producto.activo == True).scalar() or 0.0

    movimientos_periodo = db.query(models.MovimientoInventario).filter(
        models.MovimientoInventario.fecha >= fd_dt,
        models.MovimientoInventario.fecha <= fh_dt,
    ).count()

    # ── Métricas de ventas (filtradas por período) ────────────
    ventas_periodo = db.query(func.sum(models.Venta.total)).filter(
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
        models.Venta.estado == "COMPLETADA"
    ).scalar() or 0.0

    num_ventas_periodo = db.query(func.count(models.Venta.id)).filter(
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
        models.Venta.estado == "COMPLETADA"
    ).scalar() or 0

    # Ganancia del período
    ganancia_periodo = db.query(
        func.sum(models.DetalleVenta.subtotal - models.DetalleVenta.precio_costo * models.DetalleVenta.cantidad)
    ).join(models.Venta).filter(
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
        models.Venta.estado == "COMPLETADA"
    ).scalar() or 0.0

    total_clientes = db.query(models.Cliente).filter(models.Cliente.activo == True).count()

    # Top 5 productos más vendidos (en el período)
    top_productos = db.query(
        models.DetalleVenta.producto_nombre,
        func.sum(models.DetalleVenta.cantidad).label("total_qty"),
        func.sum(models.DetalleVenta.subtotal).label("total_revenue"),
    ).join(models.Venta).filter(
        models.Venta.fecha >= fd_dt,
        models.Venta.fecha <= fh_dt,
        models.Venta.estado == "COMPLETADA"
    ).group_by(models.DetalleVenta.producto_nombre) \
     .order_by(func.sum(models.DetalleVenta.cantidad).desc()).limit(5).all()

    # Ventas últimos 7 días para gráfica (desde fh hacia atrás)
    inicio_7d = fh - timedelta(days=6)
    ventas_7d_raw = dict(
        db.query(
            cast(models.Venta.fecha, Date),
            func.sum(models.Venta.total),
        ).filter(
            cast(models.Venta.fecha, Date) >= inicio_7d,
            cast(models.Venta.fecha, Date) <= fh,
            models.Venta.estado == "COMPLETADA",
        ).group_by(cast(models.Venta.fecha, Date)).all()
    )
    ventas_7d = [
        round(float(ventas_7d_raw.get(fh - timedelta(days=i), 0)), 2)
        for i in range(6, -1, -1)
    ]

    # ── Métricas financieras ───────────────────────────────────
    ahora = datetime.now()

    deudas_pendientes_total = db.query(
        func.sum(models.Deuda.monto_total - models.Deuda.monto_pagado)
    ).filter(models.Deuda.estado != "PAGADO").scalar() or 0.0

    deudas_vencidas_count = db.query(models.Deuda).filter(
        models.Deuda.estado != "PAGADO",
        models.Deuda.fecha_vencimiento != None,
        models.Deuda.fecha_vencimiento < ahora
    ).count()

    facturas_por_cobrar_total = db.query(
        func.sum(models.Factura.monto_total - models.Factura.monto_cobrado)
    ).filter(models.Factura.estado != "PAGADO").scalar() or 0.0

    facturas_vencidas_count = db.query(models.Factura).filter(
        models.Factura.estado != "PAGADO",
        models.Factura.fecha_vencimiento != None,
        models.Factura.fecha_vencimiento < ahora
    ).count()

    # ── Últimos movimientos (con joinedload para evitar N+1) ──
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

    # ── Chart: movimientos últimos 7 días (desde fh hacia atrás) ──
    mov_7d_raw = db.query(
        cast(models.MovimientoInventario.fecha, Date),
        models.MovimientoInventario.tipo,
        func.count(models.MovimientoInventario.id),
    ).filter(
        cast(models.MovimientoInventario.fecha, Date) >= inicio_7d,
        cast(models.MovimientoInventario.fecha, Date) <= fh,
    ).group_by(
        cast(models.MovimientoInventario.fecha, Date),
        models.MovimientoInventario.tipo,
    ).all()

    mov_dict = {}
    for fecha_mov, tipo_mov, cnt in mov_7d_raw:
        mov_dict[(fecha_mov, tipo_mov)] = cnt

    labels_7d = []
    entradas_7d = []
    salidas_7d = []
    for i in range(6, -1, -1):
        dia = fh - timedelta(days=i)
        labels_7d.append(dia.strftime("%d/%m"))
        entradas_7d.append(mov_dict.get((dia, "ENTRADA"), 0))
        salidas_7d.append(mov_dict.get((dia, "SALIDA"), 0))

    # ── Chart: valor inventario por categoría ──────────────────
    cats_raw = db.query(
        models.Categoria.nombre,
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).join(models.Producto, models.Producto.categoria_id == models.Categoria.id) \
     .filter(models.Producto.activo == True) \
     .group_by(models.Categoria.nombre) \
     .all()

    sin_cat = db.query(
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).filter(
        models.Producto.activo == True,
        models.Producto.categoria_id == None
    ).scalar() or 0.0

    cat_labels  = [c[0] for c in cats_raw]
    cat_valores = [round(float(c[1] or 0), 2) for c in cats_raw]
    if sin_cat > 0:
        cat_labels.append("Sin categoría")
        cat_valores.append(round(float(sin_cat), 2))

    # ── Chart: estado deudas (doughnut) ───────────────────────
    estados_deuda = {"PENDIENTE": 0, "PARCIAL": 0, "PAGADO": 0}
    for row in db.query(models.Deuda.estado, func.count(models.Deuda.id)).group_by(models.Deuda.estado).all():
        if row[0] in estados_deuda:
            estados_deuda[row[0]] = row[1]

    estados_factura = {"PENDIENTE": 0, "PARCIAL": 0, "PAGADO": 0}
    for row in db.query(models.Factura.estado, func.count(models.Factura.id)).group_by(models.Factura.estado).all():
        if row[0] in estados_factura:
            estados_factura[row[0]] = row[1]

    ctx.update({
        # Filtro temporal
        "fecha_desde":              fd.strftime("%Y-%m-%d"),
        "fecha_hasta":              fh.strftime("%Y-%m-%d"),
        # Ventas
        "ventas_periodo":           ventas_periodo,
        "ganancia_periodo":         round(ganancia_periodo, 2),
        "num_ventas_periodo":       num_ventas_periodo,
        "total_clientes":           total_clientes,
        "top_productos":            top_productos,
        "chart_ventas_7d":          json.dumps(ventas_7d),
        # Métricas
        "total_productos":          total_productos,
        "total_proveedores":        total_proveedores,
        "total_categorias":         total_categorias,
        "stock_bajo":               stock_bajo,
        "valor_inventario":         valor_inventario,
        "movimientos_periodo":      movimientos_periodo,
        "deudas_pendientes_total":  deudas_pendientes_total,
        "deudas_vencidas_count":    deudas_vencidas_count,
        "facturas_por_cobrar_total":facturas_por_cobrar_total,
        "facturas_vencidas_count":  facturas_vencidas_count,
        # Tablas
        "ultimos_movimientos":      ultimos_movimientos,
        "productos_stock_bajo":     productos_stock_bajo,
        # Chart data (JSON strings)
        "chart_labels_7d":    json.dumps(labels_7d),
        "chart_entradas_7d":  json.dumps(entradas_7d),
        "chart_salidas_7d":   json.dumps(salidas_7d),
        "chart_cat_labels":   json.dumps(cat_labels),
        "chart_cat_valores":  json.dumps(cat_valores),
        "chart_deudas":       json.dumps(list(estados_deuda.values())),
        "chart_facturas":     json.dumps(list(estados_factura.values())),
        "fecha_hoy":          hoy.strftime("%d de %B de %Y"),
    })
    return templates.TemplateResponse("index.html", ctx)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = get_local_ip()
    logger.info("=" * 55)
    logger.info("  TechStock v2.0 - Sistema de Inventario")
    logger.info("=" * 55)
    logger.info("  Acceso local:    http://localhost:8000")
    logger.info("  Acceso en red:   http://%s:8000", ip)
    logger.info("  Presiona CTRL+C para detener el servidor")
    logger.info("=" * 55)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
