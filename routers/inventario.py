from fastapi import APIRouter, Request, Depends, Form
from templates_config import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, date
from database import get_db
from auth import require_auth, log_audit, get_local_id
from utils.queries import productos_activos, proveedores_activos
import models

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.get("")
def lista_movimientos(
    request: Request,
    db: Session = Depends(get_db),
    producto_id: str = None,
    tipo: str = None,
    buscar: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    msg: str = None,
    error: str = None,
    pagina: str = None
):
    prod_id = int(producto_id) if producto_id and producto_id.strip() else None
    pag = int(pagina) if pagina and pagina.strip() else 1

    from utils.pagination import paginate

    local_id = get_local_id(request)
    query = db.query(models.MovimientoInventario).options(
        joinedload(models.MovimientoInventario.producto)
    )
    if local_id is not None:
        query = query.filter(models.MovimientoInventario.local_id == local_id)

    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.MovimientoInventario.observaciones.ilike(term)
            | models.MovimientoInventario.numero_referencia.ilike(term)
        )
    if prod_id:
        query = query.filter(models.MovimientoInventario.producto_id == prod_id)
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

    query = query.order_by(models.MovimientoInventario.fecha.desc())
    movimientos, total, total_paginas = paginate(query, pag)

    productos = productos_activos(db, local_id=local_id)

    return templates.TemplateResponse("inventario/movimientos.html", {
        "request": request,
        "movimientos": movimientos,
        "productos": productos,
        "producto_id": prod_id,
        "buscar": buscar or "",
        "tipo": tipo or "",
        "fecha_desde": fecha_desde or "",
        "fecha_hasta": fecha_hasta or "",
        "total": total,
        "pagina": pag,
        "total_paginas": total_paginas,
        "msg": msg,
        "error": error,
    })


@router.get("/entrada")
def entrada_form(request: Request, db: Session = Depends(get_db), error: str = None):
    local_id = get_local_id(request)
    productos = productos_activos(db, local_id=local_id)
    proveedores = proveedores_activos(db, local_id=local_id)
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
    local_id = get_local_id(request)
    productos = productos_activos(db, local_id=local_id)
    proveedores = proveedores_activos(db, local_id=local_id)
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
    local_id = get_local_id(request)
    productos = productos_activos(db, local_id=local_id)
    return templates.TemplateResponse("inventario/ajuste.html", {
        "request": request,
        "productos": productos,
        "error": error,
    })


@router.post("/registrar")
def registrar_movimiento(
    request: Request,
    producto_id: int = Form(...),
    tipo: str = Form(...),
    cantidad: float = Form(...),
    precio_unitario: float = Form(0.0),
    proveedor_id: str = Form(""),
    numero_referencia: str = Form(""),
    observaciones: str = Form(""),
    fecha: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    prod_query = db.query(models.Producto).filter(models.Producto.id == producto_id)
    if local_id is not None:
        prod_query = prod_query.filter(models.Producto.local_id == local_id)
    producto = prod_query.first()
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
    mov.local_id = local_id
    db.add(mov)

    producto.stock_actual = nuevo_stock
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "movimiento_inventario", mov.id,
              f"{tipo} de {cantidad} {producto.unidad_medida} - {producto.nombre}", ip)

    return RedirectResponse("/inventario?msg=Movimiento+registrado+correctamente", status_code=303)


@router.post("/ajuste/registrar")
def registrar_ajuste(
    request: Request,
    producto_id: int = Form(...),
    nuevo_stock: float = Form(...),
    observaciones: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    prod_query = db.query(models.Producto).filter(models.Producto.id == producto_id)
    if local_id is not None:
        prod_query = prod_query.filter(models.Producto.local_id == local_id)
    producto = prod_query.first()
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
    mov.local_id = local_id
    db.add(mov)
    producto.stock_actual = nuevo_stock
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "movimiento_inventario", mov.id,
              f"Ajuste de stock: {producto.nombre} de {stock_anterior} a {nuevo_stock}", ip)

    return RedirectResponse("/inventario?msg=Ajuste+de+stock+registrado+correctamente", status_code=303)
