from fastapi import APIRouter, Request, Depends, Form
from templates_config import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from database import get_db
import models

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.get("")
def lista_movimientos(
    request: Request,
    db: Session = Depends(get_db),
    producto_id: int = None,
    tipo: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    msg: str = None,
    error: str = None,
    pagina: int = 1
):
    query = db.query(models.MovimientoInventario)

    if producto_id:
        query = query.filter(models.MovimientoInventario.producto_id == producto_id)
    if tipo and tipo in ("ENTRADA", "SALIDA", "AJUSTE"):
        query = query.filter(models.MovimientoInventario.tipo == tipo)
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
            query = query.filter(models.MovimientoInventario.fecha >= fd)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d")
            fh = fh.replace(hour=23, minute=59, second=59)
            query = query.filter(models.MovimientoInventario.fecha <= fh)
        except ValueError:
            pass

    total = query.count()
    por_pagina = 20
    movimientos = query.order_by(models.MovimientoInventario.fecha.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    productos = db.query(models.Producto).filter(models.Producto.activo == True).order_by(models.Producto.nombre).all()

    return templates.TemplateResponse("inventario/movimientos.html", {
        "request": request,
        "movimientos": movimientos,
        "productos": productos,
        "producto_id": producto_id,
        "tipo": tipo or "",
        "fecha_desde": fecha_desde or "",
        "fecha_hasta": fecha_hasta or "",
        "total": total,
        "pagina": pagina,
        "total_paginas": total_paginas,
        "msg": msg,
        "error": error,
    })


@router.get("/entrada")
def entrada_form(request: Request, db: Session = Depends(get_db), error: str = None):
    productos = db.query(models.Producto).filter(models.Producto.activo == True).order_by(models.Producto.nombre).all()
    proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).order_by(models.Proveedor.nombre).all()
    return templates.TemplateResponse("inventario/entrada.html", {
        "request": request,
        "productos": productos,
        "proveedores": proveedores,
        "tipo": "ENTRADA",
        "titulo": "Registrar Entrada",
        "error": error,
    })


@router.get("/salida")
def salida_form(request: Request, db: Session = Depends(get_db), error: str = None):
    productos = db.query(models.Producto).filter(models.Producto.activo == True).order_by(models.Producto.nombre).all()
    proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).order_by(models.Proveedor.nombre).all()
    return templates.TemplateResponse("inventario/entrada.html", {
        "request": request,
        "productos": productos,
        "proveedores": proveedores,
        "tipo": "SALIDA",
        "titulo": "Registrar Salida",
        "error": error,
    })


@router.get("/ajuste")
def ajuste_form(request: Request, db: Session = Depends(get_db), error: str = None):
    productos = db.query(models.Producto).filter(models.Producto.activo == True).order_by(models.Producto.nombre).all()
    return templates.TemplateResponse("inventario/ajuste.html", {
        "request": request,
        "productos": productos,
        "error": error,
    })


@router.post("/registrar")
def registrar_movimiento(
    producto_id: int = Form(...),
    tipo: str = Form(...),
    cantidad: float = Form(...),
    precio_unitario: float = Form(0.0),
    proveedor_id: str = Form(""),
    numero_referencia: str = Form(""),
    observaciones: str = Form(""),
    fecha: str = Form(""),
    db: Session = Depends(get_db)
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        return RedirectResponse(f"/inventario/{tipo.lower()}?error=Producto+no+encontrado", status_code=303)

    if cantidad <= 0:
        return RedirectResponse(f"/inventario/{tipo.lower()}?error=La+cantidad+debe+ser+mayor+a+0", status_code=303)

    if tipo == "SALIDA" and producto.stock_actual < cantidad:
        return RedirectResponse(
            f"/inventario/salida?error=Stock+insuficiente.+Disponible:+{producto.stock_actual}+{producto.unidad_medida}",
            status_code=303
        )

    stock_anterior = producto.stock_actual

    if tipo == "ENTRADA":
        nuevo_stock = stock_anterior + cantidad
    elif tipo == "SALIDA":
        nuevo_stock = stock_anterior - cantidad
    else:  # AJUSTE
        nuevo_stock = cantidad  # En ajuste, la cantidad ES el nuevo stock

    fecha_mov = datetime.now()
    if fecha:
        try:
            fecha_mov = datetime.strptime(fecha, "%Y-%m-%dT%H:%M")
        except ValueError:
            pass

    mov = models.MovimientoInventario(
        producto_id=producto_id,
        tipo=tipo,
        cantidad=cantidad if tipo != "AJUSTE" else abs(nuevo_stock - stock_anterior),
        stock_anterior=stock_anterior,
        stock_resultante=nuevo_stock,
        precio_unitario=precio_unitario,
        proveedor_id=int(proveedor_id) if proveedor_id else None,
        numero_referencia=numero_referencia.strip(),
        observaciones=observaciones.strip(),
        fecha=fecha_mov,
    )
    db.add(mov)

    producto.stock_actual = nuevo_stock
    db.commit()

    return RedirectResponse("/inventario?msg=Movimiento+registrado+correctamente", status_code=303)


@router.post("/ajuste/registrar")
def registrar_ajuste(
    producto_id: int = Form(...),
    nuevo_stock: float = Form(...),
    observaciones: str = Form(""),
    db: Session = Depends(get_db)
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        return RedirectResponse("/inventario/ajuste?error=Producto+no+encontrado", status_code=303)

    stock_anterior = producto.stock_actual
    diferencia = abs(nuevo_stock - stock_anterior)

    mov = models.MovimientoInventario(
        producto_id=producto_id,
        tipo="AJUSTE",
        cantidad=diferencia,
        stock_anterior=stock_anterior,
        stock_resultante=nuevo_stock,
        precio_unitario=0,
        observaciones=observaciones.strip() or f"Ajuste manual de {stock_anterior} a {nuevo_stock}",
    )
    db.add(mov)
    producto.stock_actual = nuevo_stock
    db.commit()

    return RedirectResponse("/inventario?msg=Ajuste+de+stock+registrado+correctamente", status_code=303)
