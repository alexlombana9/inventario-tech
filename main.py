from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
import uvicorn
import socket
import json

from database import engine, Base, get_db
from templates_config import templates
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TechStock - Sistema de Inventario")
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers import productos, categorias, proveedores, inventario, reportes, deudas, facturas

app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(proveedores.router)
app.include_router(inventario.router)
app.include_router(reportes.router)
app.include_router(deudas.router)
app.include_router(facturas.router)


@app.get("/guia")
def guia(request: Request):
    return templates.TemplateResponse("guia/index.html", {"request": request})


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    hoy = date.today()

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

    movimientos_hoy = db.query(models.MovimientoInventario).filter(
        func.date(models.MovimientoInventario.fecha) == hoy
    ).count()

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

    # ── Últimos movimientos ────────────────────────────────────
    ultimos_movimientos = db.query(models.MovimientoInventario).order_by(
        models.MovimientoInventario.fecha.desc()
    ).limit(8).all()

    productos_stock_bajo = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual <= models.Producto.stock_minimo
    ).order_by(models.Producto.stock_actual.asc()).limit(5).all()

    # ── Chart: movimientos últimos 7 días ──────────────────────
    labels_7d    = []
    entradas_7d  = []
    salidas_7d   = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        e = db.query(func.count(models.MovimientoInventario.id)).filter(
            func.date(models.MovimientoInventario.fecha) == dia,
            models.MovimientoInventario.tipo == "ENTRADA"
        ).scalar() or 0
        s = db.query(func.count(models.MovimientoInventario.id)).filter(
            func.date(models.MovimientoInventario.fecha) == dia,
            models.MovimientoInventario.tipo == "SALIDA"
        ).scalar() or 0
        labels_7d.append(dia.strftime("%d/%m"))
        entradas_7d.append(e)
        salidas_7d.append(s)

    # ── Chart: valor inventario por categoría ──────────────────
    cats_raw = db.query(
        models.Categoria.nombre,
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).join(models.Producto, models.Producto.categoria_id == models.Categoria.id) \
     .filter(models.Producto.activo == True) \
     .group_by(models.Categoria.nombre) \
     .all()

    # Incluir productos sin categoría
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

    return templates.TemplateResponse("index.html", {
        "request": request,
        # Métricas
        "total_productos":          total_productos,
        "total_proveedores":        total_proveedores,
        "total_categorias":         total_categorias,
        "stock_bajo":               stock_bajo,
        "valor_inventario":         valor_inventario,
        "movimientos_hoy":          movimientos_hoy,
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
    print("\n" + "="*55)
    print("  TechStock - Sistema de Inventario")
    print("="*55)
    print(f"  Acceso local:    http://localhost:8000")
    print(f"  Acceso en red:   http://{ip}:8000")
    print("="*55)
    print("  Presiona CTRL+C para detener el servidor\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
