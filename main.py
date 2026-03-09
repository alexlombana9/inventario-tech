from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import uvicorn
import socket

from database import engine, Base, get_db
from templates_config import templates
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TechStock - Sistema de Inventario")
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers import productos, categorias, proveedores, inventario, reportes

app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(proveedores.router)
app.include_router(inventario.router)
app.include_router(reportes.router)


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    total_productos = db.query(models.Producto).filter(models.Producto.activo == True).count()
    total_proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).count()
    total_categorias = db.query(models.Categoria).count()

    stock_bajo = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual <= models.Producto.stock_minimo
    ).count()

    valor_inventario = db.query(
        func.sum(models.Producto.stock_actual * models.Producto.precio_costo)
    ).filter(models.Producto.activo == True).scalar() or 0.0

    hoy = date.today()
    movimientos_hoy = db.query(models.MovimientoInventario).filter(
        func.date(models.MovimientoInventario.fecha) == hoy
    ).count()

    ultimos_movimientos = db.query(models.MovimientoInventario).order_by(
        models.MovimientoInventario.fecha.desc()
    ).limit(8).all()

    productos_stock_bajo = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual <= models.Producto.stock_minimo
    ).order_by(models.Producto.stock_actual.asc()).limit(5).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_productos": total_productos,
        "total_proveedores": total_proveedores,
        "total_categorias": total_categorias,
        "stock_bajo": stock_bajo,
        "valor_inventario": valor_inventario,
        "movimientos_hoy": movimientos_hoy,
        "ultimos_movimientos": ultimos_movimientos,
        "productos_stock_bajo": productos_stock_bajo,
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
