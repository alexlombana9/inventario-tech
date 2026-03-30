import json
import io
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import func
from datetime import datetime, date, timedelta

from database import get_db
from templates_config import templates
from auth import require_auth, require_role, log_audit, get_local_id
from utils.queries import productos_con_stock, clientes_activos, vendedores_activos
import models

router = APIRouter(prefix="/ventas", tags=["ventas"])

from utils.constants import METODOS_PAGO_VENTAS as METODOS_PAGO


from utils.financial import siguiente_numero as _sig_num


def _siguiente_numero(db: Session, local_id: int = None) -> str:
    return _sig_num(db, models.Venta, "numero_venta", "VTA", local_id=local_id)


# ── POS Interface ────────────────────────────────────────────

@router.get("/pos")
def pos_interface(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    productos = productos_con_stock(db, local_id=local_id)
    clientes = clientes_activos(db, local_id=local_id)

    # Verificar si hay caja abierta
    caja_query = db.query(models.Caja).filter(
        models.Caja.usuario_id == current_user.id,
        models.Caja.estado == "ABIERTA"
    )
    if local_id is not None:
        caja_query = caja_query.filter(models.Caja.local_id == local_id)
    caja_abierta = caja_query.first()

    return templates.TemplateResponse("ventas/pos.html", {
        "request": request,
        "productos": productos,
        "clientes": clientes,
        "caja_abierta": caja_abierta,
        "numero_venta": _siguiente_numero(db, local_id=local_id),
        "metodos_pago": METODOS_PAGO,
    })


# ── API: Search products (for POS AJAX) ─────────────────────

@router.get("/api/productos")
def api_buscar_productos(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    query = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual > 0
    )
    local_id = get_local_id(request)
    if local_id is not None:
        query = query.filter(models.Producto.local_id == local_id)
    if q:
        query = query.filter(
            models.Producto.nombre.ilike(f"%{q}%") |
            models.Producto.codigo.ilike(f"%{q}%") |
            models.Producto.referencia.ilike(f"%{q}%")
        )
    productos = query.limit(20).all()

    return JSONResponse([{
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "referencia": p.referencia or "",
        "precio_venta": p.precio_venta,
        "precio_costo": p.precio_costo,
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
    local_id = get_local_id(request)
    caja_query = db.query(models.Caja).filter(
        models.Caja.usuario_id == current_user.id,
        models.Caja.estado == "ABIERTA"
    )
    if local_id is not None:
        caja_query = caja_query.filter(models.Caja.local_id == local_id)
    caja_abierta = caja_query.first()

    # Create sale with atomic transaction and pessimistic locking
    try:
        numero = _siguiente_numero(db, local_id=local_id)
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
        venta.local_id = local_id
        db.add(venta)
        db.flush()

        # Create details and update stock with row-level locking
        for item in items:
            producto = db.query(models.Producto).filter(
                models.Producto.id == item["producto_id"]
            ).with_for_update().first()

            if not producto or producto.stock_actual < item["cantidad"]:
                db.rollback()
                nombre = producto.nombre if producto else item.get("nombre", "")
                return RedirectResponse(
                    f"/ventas/pos?error=Stock+insuficiente+para+{nombre}", status_code=303
                )

            desc_item = item.get("descuento", 0)
            sub = item["cantidad"] * item["precio_unitario"] - desc_item

            detalle = models.DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                producto_nombre=producto.nombre,
                producto_codigo=producto.codigo,
                producto_referencia=producto.referencia or "",
                cantidad=item["cantidad"],
                precio_unitario=item["precio_unitario"],
                precio_costo=producto.precio_costo,
                descuento_item=desc_item,
                subtotal=round(sub, 2),
            )
            detalle.local_id = local_id
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
            mov.local_id = local_id
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
            mov_caja.local_id = local_id
            db.add(mov_caja)

        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/ventas/pos?error=Error+procesando+la+venta", status_code=303)

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
    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Venta).options(
        joinedload(models.Venta.vendedor),
        subqueryload(models.Venta.detalles),
    )
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)

    fd = None
    fh = None
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

    from utils.pagination import paginate
    query = query.order_by(models.Venta.fecha.desc())
    ventas, total, total_paginas = paginate(query, pag)

    total_ventas_q = db.query(func.sum(models.Venta.total)).filter(
        models.Venta.fecha >= fd if fd else True,
        models.Venta.fecha <= fh if fh else True,
        models.Venta.estado == "COMPLETADA"
    )
    if local_id is not None:
        total_ventas_q = total_ventas_q.filter(models.Venta.local_id == local_id)
    total_ventas = total_ventas_q.scalar() or 0

    # Costo del período: sum(precio_costo * cantidad) de detalles de ventas completadas
    costo_q = db.query(
        func.sum(models.DetalleVenta.precio_costo * models.DetalleVenta.cantidad)
    ).join(models.Venta).filter(
        models.Venta.fecha >= fd if fd else True,
        models.Venta.fecha <= fh if fh else True,
        models.Venta.estado == "COMPLETADA"
    )
    if local_id is not None:
        costo_q = costo_q.filter(models.Venta.local_id == local_id)
    costo_periodo = costo_q.scalar() or 0

    # Ganancia del período: sum(subtotal - costo) de detalles de ventas completadas
    ganancia_q = db.query(
        func.sum(models.DetalleVenta.subtotal - models.DetalleVenta.precio_costo * models.DetalleVenta.cantidad)
    ).join(models.Venta).filter(
        models.Venta.fecha >= fd if fd else True,
        models.Venta.fecha <= fh if fh else True,
        models.Venta.estado == "COMPLETADA"
    )
    if local_id is not None:
        ganancia_q = ganancia_q.filter(models.Venta.local_id == local_id)
    ganancia_periodo = ganancia_q.scalar() or 0

    vendedores = vendedores_activos(db, local_id=local_id)

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
        "costo_periodo": round(costo_periodo, 2),
        "ganancia_periodo": round(ganancia_periodo, 2),
        "pagina": pag,
        "total_paginas": total_paginas,
        "msg": msg,
        "error": error,
    })


# ── Excel Export ─────────────────────────────────────────────

@router.get("/excel")
def ventas_excel(
    request: Request,
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
    local_id = get_local_id(request)
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Venta.fecha >= fd, models.Venta.fecha <= fh)
    except ValueError:
        pass

    if estado:
        query = query.filter(models.Venta.estado == estado)

    ventas = query.options(joinedload(models.Venta.vendedor)).order_by(models.Venta.fecha.desc()).all()

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
    msg: str = None,
    error: str = None,
):
    local_id = get_local_id(request)
    query = db.query(models.Venta).options(
        joinedload(models.Venta.detalles),
        joinedload(models.Venta.vendedor),
    ).filter(models.Venta.id == venta_id)
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)
    venta = query.first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)

    return templates.TemplateResponse("ventas/detalle.html", {
        "request": request,
        "venta": venta,
        "msg": msg,
        "error": error,
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
    local_id = get_local_id(request)
    query = db.query(models.Venta).options(
        joinedload(models.Venta.detalles),
        joinedload(models.Venta.vendedor),
    ).filter(models.Venta.id == venta_id)
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)
    venta = query.first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)

    config_query = db.query(models.Configuracion)
    if local_id is not None:
        config_query = config_query.filter(models.Configuracion.local_id == local_id)
    config = config_query.first()

    return templates.TemplateResponse("ventas/recibo.html", {
        "request": request,
        "venta": venta,
        "config": config,
        "msg": msg,
    })


# ── Edit Sale (ADMIN only) ──────────────────────────────────

@router.get("/{venta_id}/editar")
def editar_venta_form(
    venta_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    error: str = None,
):
    local_id = get_local_id(request)
    query = db.query(models.Venta).options(
        joinedload(models.Venta.detalles),
        joinedload(models.Venta.vendedor),
    ).filter(models.Venta.id == venta_id)
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)
    venta = query.first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)
    if venta.estado == "ANULADA":
        return RedirectResponse("/ventas?error=No+se+puede+editar+una+venta+anulada", status_code=303)

    clientes = clientes_activos(db, local_id=local_id)

    return templates.TemplateResponse("ventas/editar.html", {
        "request": request,
        "venta": venta,
        "clientes": clientes,
        "metodos_pago": METODOS_PAGO,
        "error": error,
    })


@router.post("/{venta_id}/editar")
def editar_venta(
    venta_id: int,
    request: Request,
    cliente_nombre: str = Form("Consumidor Final"),
    cliente_id: str = Form(""),
    metodo_pago: str = Form("EFECTIVO"),
    descuento_total: float = Form(0.0),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    local_id = get_local_id(request)
    query = db.query(models.Venta).options(
        joinedload(models.Venta.detalles),
    ).filter(models.Venta.id == venta_id)
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)
    venta = query.first()
    if not venta:
        return RedirectResponse("/ventas?error=Venta+no+encontrada", status_code=303)
    if venta.estado == "ANULADA":
        return RedirectResponse("/ventas?error=No+se+puede+editar+una+venta+anulada", status_code=303)

    # Validar descuento
    if descuento_total < 0:
        return RedirectResponse(
            f"/ventas/{venta_id}/editar?error=El+descuento+no+puede+ser+negativo",
            status_code=303,
        )

    # Registrar cambios para audit
    cambios = []
    if venta.cliente_nombre != cliente_nombre.strip():
        cambios.append(f"cliente: '{venta.cliente_nombre}' → '{cliente_nombre.strip()}'")
    if venta.metodo_pago != metodo_pago:
        cambios.append(f"metodo_pago: '{venta.metodo_pago}' → '{metodo_pago}'")
    if venta.descuento_total != round(descuento_total, 2):
        cambios.append(f"descuento: {venta.descuento_total} → {round(descuento_total, 2)}")
    if (venta.notas or "") != notas.strip():
        cambios.append("notas actualizado")

    # Aplicar cambios
    venta.cliente_nombre = cliente_nombre.strip() or "Consumidor Final"
    try:
        venta.cliente_id = int(cliente_id) if cliente_id.strip() else None
    except ValueError:
        venta.cliente_id = None
    venta.metodo_pago = metodo_pago
    venta.descuento_total = round(descuento_total, 2)
    venta.notas = notas.strip()

    # Recalcular total: subtotal - descuento_total
    nuevo_total = venta.subtotal - venta.descuento_total
    if nuevo_total < 0:
        nuevo_total = 0
    if venta.total != round(nuevo_total, 2):
        cambios.append(f"total: {venta.total} → {round(nuevo_total, 2)}")
    venta.total = round(nuevo_total, 2)

    # Recalcular cambio si es efectivo
    if metodo_pago == "EFECTIVO":
        venta.cambio = round(max(0, venta.monto_recibido - venta.total), 2)
    else:
        venta.cambio = 0

    db.commit()

    ip = request.client.host if request.client else ""
    detalle_audit = f"Venta {venta.numero_venta} editada"
    if cambios:
        detalle_audit += f": {', '.join(cambios)}"
    log_audit(db, current_user, "UPDATE", "venta", venta.id, detalle_audit, ip)

    return RedirectResponse(
        f"/ventas/{venta.id}/detalle?msg=Venta+editada+correctamente",
        status_code=303,
    )


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

    local_id = get_local_id(request)
    query = db.query(models.Venta).options(
        joinedload(models.Venta.detalles)
    ).filter(models.Venta.id == venta_id)
    if local_id is not None:
        query = query.filter(models.Venta.local_id == local_id)
    venta = query.first()
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
            mov.local_id = local_id
            db.add(mov)

    venta.estado = "ANULADA"
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "venta", venta.id,
              f"Venta anulada: {venta.numero_venta}", ip)

    return RedirectResponse(f"/ventas?msg=Venta+{venta.numero_venta}+anulada+correctamente", status_code=303)
