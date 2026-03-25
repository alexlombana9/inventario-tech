from fastapi import APIRouter, Request, Depends, Form
from templates_config import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("")
def lista_productos(
    request: Request,
    db: Session = Depends(get_db),
    buscar: str = None,
    categoria_id: int = None,
    stock_bajo: bool = False,
    msg: str = None,
    error: str = None
):
    query = db.query(models.Producto).filter(models.Producto.activo == True)

    if buscar:
        query = query.filter(
            models.Producto.nombre.ilike(f"%{buscar}%") |
            models.Producto.codigo.ilike(f"%{buscar}%")
        )
    if categoria_id:
        query = query.filter(models.Producto.categoria_id == categoria_id)
    if stock_bajo:
        query = query.filter(models.Producto.stock_actual <= models.Producto.stock_minimo)

    productos = query.order_by(models.Producto.nombre).all()
    categorias = db.query(models.Categoria).order_by(models.Categoria.nombre).all()

    return templates.TemplateResponse("productos/lista.html", {
        "request": request,
        "productos": productos,
        "categorias": categorias,
        "buscar": buscar or "",
        "categoria_id": categoria_id,
        "stock_bajo": stock_bajo,
        "msg": msg,
        "error": error,
    })


@router.get("/nuevo")
def nuevo_producto_form(request: Request, db: Session = Depends(get_db)):
    categorias = db.query(models.Categoria).order_by(models.Categoria.nombre).all()
    proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).order_by(models.Proveedor.nombre).all()
    return templates.TemplateResponse("productos/form.html", {
        "request": request,
        "producto": None,
        "categorias": categorias,
        "proveedores": proveedores,
        "accion": "Nuevo",
    })


@router.post("/nuevo")
def crear_producto(
    codigo: str = Form(...),
    nombre: str = Form(...),
    referencia: str = Form(""),
    descripcion: str = Form(""),
    categoria_id: str = Form(""),
    proveedor_id: str = Form(""),
    precio_costo: float = Form(0.0),
    precio_venta: float = Form(0.0),
    precio_venta_minimo: float = Form(0.0),
    stock_actual: float = Form(0.0),
    stock_minimo: float = Form(0.0),
    unidad_medida: str = Form("UND"),
    db: Session = Depends(get_db)
):
    existe = db.query(models.Producto).filter(models.Producto.codigo == codigo.strip()).first()
    if existe:
        return RedirectResponse(f"/productos/nuevo?error=Ya+existe+un+producto+con+el+código+{codigo}", status_code=303)

    producto = models.Producto(
        codigo=codigo.strip().upper(),
        referencia=referencia.strip(),
        nombre=nombre.strip(),
        descripcion=descripcion.strip(),
        categoria_id=int(categoria_id) if categoria_id else None,
        proveedor_id=int(proveedor_id) if proveedor_id else None,
        precio_costo=precio_costo,
        precio_venta=precio_venta,
        precio_venta_minimo=precio_venta_minimo,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
        unidad_medida=unidad_medida.strip().upper() or "UND",
    )
    db.add(producto)
    db.flush()

    # Registrar movimiento inicial si hay stock
    if stock_actual > 0:
        mov = models.MovimientoInventario(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=stock_actual,
            stock_anterior=0,
            stock_resultante=stock_actual,
            precio_unitario=precio_costo,
            observaciones="Stock inicial al crear producto",
        )
        db.add(mov)

    db.commit()
    return RedirectResponse("/productos?msg=Producto+creado+correctamente", status_code=303)


@router.get("/{prod_id}/editar")
def editar_producto_form(prod_id: int, request: Request, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == prod_id).first()
    if not producto:
        return RedirectResponse("/productos?error=Producto+no+encontrado", status_code=303)
    categorias = db.query(models.Categoria).order_by(models.Categoria.nombre).all()
    proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).order_by(models.Proveedor.nombre).all()
    return templates.TemplateResponse("productos/form.html", {
        "request": request,
        "producto": producto,
        "categorias": categorias,
        "proveedores": proveedores,
        "accion": "Editar",
    })


@router.post("/{prod_id}/editar")
def actualizar_producto(
    prod_id: int,
    codigo: str = Form(...),
    nombre: str = Form(...),
    referencia: str = Form(""),
    descripcion: str = Form(""),
    categoria_id: str = Form(""),
    proveedor_id: str = Form(""),
    precio_costo: float = Form(0.0),
    precio_venta: float = Form(0.0),
    precio_venta_minimo: float = Form(0.0),
    stock_minimo: float = Form(0.0),
    unidad_medida: str = Form("UND"),
    db: Session = Depends(get_db)
):
    producto = db.query(models.Producto).filter(models.Producto.id == prod_id).first()
    if not producto:
        return RedirectResponse("/productos?error=Producto+no+encontrado", status_code=303)

    existe = db.query(models.Producto).filter(
        models.Producto.codigo == codigo.strip().upper(),
        models.Producto.id != prod_id
    ).first()
    if existe:
        return RedirectResponse(f"/productos/{prod_id}/editar?error=Ya+existe+otro+producto+con+ese+código", status_code=303)

    producto.codigo = codigo.strip().upper()
    producto.referencia = referencia.strip()
    producto.nombre = nombre.strip()
    producto.descripcion = descripcion.strip()
    producto.categoria_id = int(categoria_id) if categoria_id else None
    producto.proveedor_id = int(proveedor_id) if proveedor_id else None
    producto.precio_costo = precio_costo
    producto.precio_venta = precio_venta
    producto.precio_venta_minimo = precio_venta_minimo
    producto.stock_minimo = stock_minimo
    producto.unidad_medida = unidad_medida.strip().upper() or "UND"
    db.commit()
    return RedirectResponse("/productos?msg=Producto+actualizado+correctamente", status_code=303)


@router.post("/{prod_id}/eliminar")
def eliminar_producto(prod_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == prod_id).first()
    if not producto:
        return RedirectResponse("/productos?error=Producto+no+encontrado", status_code=303)
    producto.activo = False
    db.commit()
    return RedirectResponse("/productos?msg=Producto+desactivado+correctamente", status_code=303)
