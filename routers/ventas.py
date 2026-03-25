import json
import io
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta

from database import get_db
from templates_config import templates
from auth import require_auth, log_audit
import models

router = APIRouter(prefix="/ventas", tags=["ventas"])

METODOS_PAGO = ["EFECTIVO", "TARJETA", "TRANSFERENCIA", "CREDITO"]


def _siguiente_numero(db: Session) -> str:
    ultimo = db.query(models.Venta).order_by(models.Venta.id.desc()).first()
    if not ultimo:
        return "VTA-0001"
    try:
        num = int(ultimo.numero_venta.split("-")[-1]) + 1
        return f"VTA-{num:04d}"
    except (ValueError, IndexError):
        return f"VTA-{(ultimo.id or 0) + 1:04d}"


# ── POS Interface ────────────────────────────────────────────

@router.get("/pos")
def pos_interface(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    productos = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual > 0
    ).order_by(models.Producto.nombre).all()

    clientes = db.query(models.Cliente).filter(
        models.Cliente.activo == True
    ).order_by(models.Cliente.nombre).all()

    # Verificar si hay caja abierta
    caja_abierta = db.query(models.Caja).filter(
        models.Caja.usuario_id == current_user.id,
        models.Caja.estado == "ABIERTA"
    ).first()

    return templates.TemplateResponse("ventas/pos.html", {
        "request": request,
        "productos": productos,
        "clientes": clientes,
        "caja_abierta": caja_abierta,
        "numero_venta": _siguiente_numero(db),
        "metodos_pago": METODOS_PAGO,
    })


# ── API: Search products (for POS AJAX) ─────────────────────

@router.get("/api/productos")
def api_buscar_productos(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    query = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual > 0
    )
    if q:
        query = query.filter(
            models.Producto.nombre.ilike(f"%{q}%") |
            models.Producto.codigo.ilike(f"%{q}%")
        )
    productos = query.limit(20).all()

    return JSONResponse([{
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "precio_venta": p.precio_venta,
        "stock_actual": p.stock_actual,
        "unidad_medida": p.unidad_medida,
    } for p in productos])


# ── Process Sale ─────────────────────────────────────────────

@router.post("/procesar")
def procesar_venta(
    request: Request,
    items_json: str = Form(...),
    cliente_id: str = Form(""),
    cliente_nombre: str = Form("Consumidor Final"),
    metodo_pago: str = Form("EFECTIVO"),
    monto_recibido: float = Form(0.0),
    descuento_total: float = Form(0.0),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    try:
        items = json.loads(items_json)
    except json.JSONDecodeError:
        return RedirectResponse("/ventas/pos?error=Error+en+los+datos+del+carrito", status_code=303)

    if not items:
        return RedirectResponse("/ventas/pos?error=El+carrito+está+vacío", status_code=303)

    # Validate stock
    for item in items:
        producto = db.query(models.Producto).filter(models.Producto.id == item["producto_id"]).first()
        if not producto:
            return RedirectResponse(f"/ventas/pos?error=Producto+no+encontrado:+{item.get('nombre', '')}", status_code=303)
        if producto.stock_actual < item["cantidad"]:
            return RedirectResponse(
                f"/ventas/pos?error=Stock+insuficiente+para+{producto.nombre}.+Disponible:+{producto.stock_actual}",
                status_code=303
            )

    # Calculate totals
    subtotal = sum(item["cantidad"] * item["precio_unitario"] - item.get("descuento", 0) for item in items)
    total = subtotal - descuento_total

    if total < 0:
        total = 0

    cambio = max(0, monto_recibido - total) if metodo_pago == "EFECTIVO" else 0

    # Check for open cash register
    caja_abierta = db.query(models.Caja).filter(
        models.Caja.usuario_id == current_user.id,
        models.Caja.estado == "ABIERTA"
    ).first()

    # Create sale
    numero = _siguiente_numero(db)
    client_id = int(cliente_id) if cliente_id.strip() else None

    venta = models.Venta(
        numero_venta=numero,
        cliente_id=client_id,
        cliente_nombre=cliente_nombre.strip() or "Consumidor Final",
        vendedor_id=current_user.id,
        subtotal=round(subtotal, 2),
        descuento_total=round(descuento_total, 2),
        total=round(total, 2),
        metodo_pago=metodo_pago,
        monto_recibido=round(monto_recibido, 2),
        cambio=round(cambio, 2),
        notas=notas.strip(),
        caja_id=caja_abierta.id if caja_abierta else None,
        fecha=datetime.now(),
    )
    db.add(venta)
    db.flush()

    # Create details and update stock
    for item in items:
        producto = db.query(models.Producto).filter(models.Producto.id == item["producto_id"]).first()
        desc_item = item.get("descuento", 0)
        sub = item["cantidad"] * item["precio_unitario"] - desc_item

        detalle = models.DetalleVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            producto_nombre=producto.nombre,
            producto_codigo=producto.codigo,
            cantidad=item["cantidad"],
            precio_unitario=item["precio_unitario"],
            precio_costo=producto.precio_costo,
            descuento_item=desc_item,
            subtotal=round(sub, 2),
        )
        db.add(detalle)

        # Stock movement
        stock_anterior = producto.stock_actual
        producto.stock_actual = stock_anterior - item["cantidad"]

        mov = models.MovimientoInventario(
            producto_id=producto.id,
            tipo="SALIDA",
            cantidad=item["cantidad"],
            stock_anterior=stock_anterior,
            stock_resultante=producto.stock_actual,
            precio_unitario=item["precio_unitario"],
            observaciones=f"Venta {numero}",
            fecha=datetime.now(),
        )
        db.add(mov)

    # Cash register movement
    if caja_abierta and metodo_pago == "EFECTIVO":
        mov_caja = models.MovimientoCaja(
            caja_id=caja_abierta.id,
            tipo="INGRESO",
            concepto=f"Venta {numero}",
            monto=round(total, 2),
            referencia_tipo="VENTA",
            referencia_id=venta.id,
        )
        db.add(mov_caja)

    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "venta", venta.id,
              f"Venta {numero} por ${total:,.2f} ({metodo_pago})", ip)

    return RedirectResponse(f"/ventas/{venta.id}/recibo?msg=Venta+registrada+correctamente", status_code=303)


# ── Sale History ─────────────────────────────────────────────

@router.get("")
def historial_ventas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    fecha_desde: str = None,
    fecha_hasta: str = None,
    estado: str = None,
    metodo_pago: str = None,
    vendedor_id: str = None,
    buscar: str = None,
    msg: str = None,
    error: str = None,
    pagina: str = None,
):
    pag = int(pagina) if pagina and pagina.strip() else 1

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Venta)

    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Venta.fecha >= fd, models.Venta.fecha <= fh)
    except ValueError:
        pass

    if estado and estado.strip():
        query = query.filter(models.Venta.estado == estado)
    if metodo_pago and metodo_pago.strip():
        query = query.filter(models.Venta.metodo_pago == metodo_pago)
    if vendedor_id and vendedor_id.strip():
        try:
            query = query.filter(models.Venta.vendedor_id == int(vendedor_id))
        except ValueError:
            pass
    if buscar:
        query = query.filter(
            models.Venta.numero_venta.ilike(f"%{buscar}%") |
            models.Venta.cliente_nombre.ilike(f"%{buscar}%")
        )

    total = query.count()
    por_pagina = 20
    ventas = query.order_by(models.Venta.fecha.desc()).offset((pag - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    total_ventas = db.query(func.sum(models.Venta.total)).filter(
        models.Venta.fecha >= fd if fecha_desde else True,
        models.Venta.fecha <= fh if fecha_hasta else True,
        models.Venta.estado == "COMPLETADA"
    ).scalar() or 0

    # Obtener vendedores para filtro
    vendedores = db.query(models.Usuario).filter(
        models.Usuario.activo == True
    ).order_by(models.Usuario.nombre_completo).all()

    return templates.TemplateResponse("ventas/historial.html", {
        "request": request,
        "ventas": ventas,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "estado": estado or "",
        "metodo_pago": metodo_pago or "",
        "vendedor_id": vendedor_id or "",
        "vendedores": vendedores,
        "metodos_pago": METODOS_PAGO,
        "buscar": buscar or "",
        "total": total,
        "total_ventas": total_ventas,
        "pagina": pag,
        "total_paginas": total_paginas,
        "msg": msg,
        "error": error,
    })


# ── Excel Export ─────────────────────────────────────────────

@router.get("/excel")
def ventas_excel(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    fecha_desde: str = None,
    fecha_hasta: str = None,
    estado: str = None,
):
    from utils.excel import generate_excel

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Venta)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Venta.fecha >= fd, models.Venta.fecha <= fh)
    except ValueError:
        pass

    if estado:
        query = query.filter(models.Venta.estado == estado)

    ventas = query.order_by(models.Venta.fecha.desc()).all()

    headers = ["N° Venta", "Fecha", "Cliente", "Vendedor", "Subtotal", "Descuento", "Total", "Método Pago", "Estado"]
    rows = []
    for v in ventas:
        rows.append([
            v.numero_venta,
            v.fecha.strftime("%d/%m/%Y %H:%M"),
            v.cliente_nombre,
            v.vendedor.nombre_completo if v.vendedor else "-",
            v.subtotal, v.descuento_total, v.total,
            v.metodo_pago, v.estado,
        ])

    output = generate_excel(
        "Historial de Ventas", headers, rows,
        col_widths=[14, 18, 24, 20, 14, 14, 14, 16, 14],
        money_cols=[4, 5, 6],
    )
    filename = f"ventas_{fecha_desde}_{fecha_hasta}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Sale Detail ──────────────────────────────────────────────

@router.get("/{venta_id}/detalle")
def detalle_venta(
    venta_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    venta = db.query(models.Venta).filter(models.Venta.id == venta_id).first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)

    return templates.TemplateResponse("ventas/detalle.html", {
        "request": request,
        "venta": venta,
    })


# ── Receipt ──────────────────────────────────────────────────

@router.get("/{venta_id}/recibo")
def recibo_venta(
    venta_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    msg: str = None,
):
    venta = db.query(models.Venta).filter(models.Venta.id == venta_id).first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)

    config = db.query(models.Configuracion).first()

    return templates.TemplateResponse("ventas/recibo.html", {
        "request": request,
        "venta": venta,
        "config": config,
        "msg": msg,
    })


# ── Void Sale ────────────────────────────────────────────────

@router.post("/{venta_id}/anular")
def anular_venta(
    venta_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    if current_user.rol != "ADMIN":
        return RedirectResponse("/ventas?error=Solo+el+administrador+puede+anular+ventas", status_code=303)

    venta = db.query(models.Venta).filter(models.Venta.id == venta_id).first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)
    if venta.estado == "ANULADA":
        return RedirectResponse("/ventas?error=La+venta+ya+está+anulada", status_code=303)

    # Reverse stock
    for detalle in venta.detalles:
        producto = db.query(models.Producto).filter(models.Producto.id == detalle.producto_id).first()
        if producto:
            stock_anterior = producto.stock_actual
            producto.stock_actual += detalle.cantidad

            mov = models.MovimientoInventario(
                producto_id=producto.id,
                tipo="ENTRADA",
                cantidad=detalle.cantidad,
                stock_anterior=stock_anterior,
                stock_resultante=producto.stock_actual,
                precio_unitario=detalle.precio_unitario,
                observaciones=f"Anulación venta {venta.numero_venta}",
                fecha=datetime.now(),
            )
            db.add(mov)

    venta.estado = "ANULADA"
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "venta", venta.id,
              f"Venta anulada: {venta.numero_venta}", ip)

    return RedirectResponse(f"/ventas?msg=Venta+{venta.numero_venta}+anulada+correctamente", status_code=303)
