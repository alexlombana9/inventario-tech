from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, timedelta
from database import get_db
from templates_config import templates
from auth import require_auth, log_audit, get_local_id
import models

router = APIRouter(prefix="/facturas", tags=["facturas"])

from utils.constants import METODOS_PAGO


from utils.financial import actualizar_estado_pago, siguiente_numero


def _actualizar_estado(factura: models.Factura):
    """Recalcula el estado de la factura según montos cobrados."""
    actualizar_estado_pago(factura, "monto_cobrado")


def _siguiente_numero(db: Session, local_id: int = None) -> str:
    """Genera el próximo número de factura correlativo."""
    return siguiente_numero(db, models.Factura, "numero_factura", "FAC", local_id=local_id)


# ── Lista ────────────────────────────────────────────────────────────────────

@router.get("")
def lista_facturas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    buscar: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    vencidas: str = None,
    msg: str = None,
    error: str = None,
):
    local_id = get_local_id(request)
    query = db.query(models.Factura)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    if estado:
        query = query.filter(models.Factura.estado == estado)
    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.Factura.cliente_nombre.ilike(term) |
            models.Factura.numero_factura.ilike(term) |
            models.Factura.concepto.ilike(term) |
            models.Factura.cliente_documento.ilike(term)
        )
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
            query = query.filter(models.Factura.fecha_emision >= fd)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Factura.fecha_emision <= fh)
        except ValueError:
            pass
    if vencidas == "1":
        query = query.filter(
            models.Factura.fecha_vencimiento < datetime.now(),
            models.Factura.estado != "PAGADO",
        )

    facturas = query.order_by(models.Factura.fecha_vencimiento.asc().nullsfirst(),
                              models.Factura.created_at.desc()).all()

    total_facturado = sum(f.monto_total for f in facturas)
    total_cobrado = sum(f.monto_cobrado for f in facturas)
    total_por_cobrar = sum(f.monto_pendiente for f in facturas if f.estado != "PAGADO")
    total_vencidas = sum(1 for f in facturas if f.esta_vencida)

    return templates.TemplateResponse("facturas/lista.html", {
        "request": request,
        "facturas": facturas,
        "total_facturado": total_facturado,
        "total_cobrado": total_cobrado,
        "total_por_cobrar": total_por_cobrar,
        "total_vencidas": total_vencidas,
        "estado": estado or "",
        "buscar": buscar or "",
        "fecha_desde": fecha_desde or "",
        "fecha_hasta": fecha_hasta or "",
        "vencidas": vencidas or "",
        "msg": msg,
        "error": error,
    })


# ── Nueva factura ────────────────────────────────────────────────────────────

@router.get("/nueva")
def nueva_factura_form(request: Request, db: Session = Depends(get_db)):
    local_id = get_local_id(request)
    return templates.TemplateResponse("facturas/form.html", {
        "request": request,
        "factura": None,
        "numero_sugerido": _siguiente_numero(db, local_id=local_id),
        "accion": "Nueva",
        "error": None,
    })


@router.post("/nueva")
def crear_factura(
    request: Request,
    numero_factura: str = Form(...),
    cliente_nombre: str = Form(...),
    cliente_empresa: str = Form(""),
    cliente_documento: str = Form(""),
    cliente_telefono: str = Form(""),
    cliente_email: str = Form(""),
    concepto: str = Form(...),
    monto_total: float = Form(...),
    fecha_emision: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    existe_query = db.query(models.Factura).filter(
        models.Factura.numero_factura == numero_factura.strip()
    )
    if local_id is not None:
        existe_query = existe_query.filter(models.Factura.local_id == local_id)
    existe = existe_query.first()
    if existe:
        return RedirectResponse(
            f"/facturas/nueva?error=Ya+existe+una+factura+con+el+número+{numero_factura}",
            status_code=303,
        )

    fec_emision = datetime.strptime(fecha_emision, "%Y-%m-%d") if fecha_emision else datetime.now()
    fec_venc = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None

    factura = models.Factura(
        numero_factura=numero_factura.strip(),
        cliente_nombre=cliente_nombre.strip(),
        cliente_empresa=cliente_empresa.strip(),
        cliente_documento=cliente_documento.strip(),
        cliente_telefono=cliente_telefono.strip(),
        cliente_email=cliente_email.strip(),
        concepto=concepto.strip(),
        monto_total=monto_total,
        fecha_emision=fec_emision,
        fecha_vencimiento=fec_venc,
        notas=notas.strip(),
    )
    factura.local_id = local_id
    db.add(factura)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "factura", factura.id,
              f"Factura creada: {numero_factura.strip()} por ${monto_total:,.2f}", ip)

    return RedirectResponse("/facturas?msg=Factura+creada+correctamente", status_code=303)


# ── Editar ───────────────────────────────────────────────────────────────────

@router.get("/{factura_id}/editar")
def editar_factura_form(factura_id: int, request: Request, db: Session = Depends(get_db)):
    local_id = get_local_id(request)
    query = db.query(models.Factura).filter(models.Factura.id == factura_id)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    factura = query.first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)
    return templates.TemplateResponse("facturas/form.html", {
        "request": request,
        "factura": factura,
        "numero_sugerido": factura.numero_factura,
        "accion": "Editar",
        "error": None,
    })


@router.post("/{factura_id}/editar")
def actualizar_factura(
    factura_id: int,
    request: Request,
    numero_factura: str = Form(...),
    cliente_nombre: str = Form(...),
    cliente_empresa: str = Form(""),
    cliente_documento: str = Form(""),
    cliente_telefono: str = Form(""),
    cliente_email: str = Form(""),
    concepto: str = Form(...),
    monto_total: float = Form(...),
    fecha_emision: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Factura).filter(models.Factura.id == factura_id)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    factura = query.first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)

    dup_query = db.query(models.Factura).filter(
        models.Factura.numero_factura == numero_factura.strip(),
        models.Factura.id != factura_id,
    )
    if local_id is not None:
        dup_query = dup_query.filter(models.Factura.local_id == local_id)
    duplicado = dup_query.first()
    if duplicado:
        return RedirectResponse(
            f"/facturas/{factura_id}/editar?error=Número+de+factura+ya+en+uso",
            status_code=303,
        )

    factura.numero_factura = numero_factura.strip()
    factura.cliente_nombre = cliente_nombre.strip()
    factura.cliente_empresa = cliente_empresa.strip()
    factura.cliente_documento = cliente_documento.strip()
    factura.cliente_telefono = cliente_telefono.strip()
    factura.cliente_email = cliente_email.strip()
    factura.concepto = concepto.strip()
    factura.monto_total = monto_total
    factura.fecha_emision = datetime.strptime(fecha_emision, "%Y-%m-%d") if fecha_emision else factura.fecha_emision
    factura.fecha_vencimiento = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None
    factura.notas = notas.strip()
    _actualizar_estado(factura)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "factura", factura.id,
              f"Factura actualizada: {numero_factura.strip()}", ip)

    return RedirectResponse(f"/facturas/{factura_id}/detalle?msg=Factura+actualizada+correctamente", status_code=303)


# ── Detalle + historial de cobros ────────────────────────────────────────────

@router.get("/{factura_id}/detalle")
def detalle_factura(factura_id: int, request: Request, db: Session = Depends(get_db),
                    msg: str = None, error: str = None):
    local_id = get_local_id(request)
    query = db.query(models.Factura).options(
        joinedload(models.Factura.cobros)
    ).filter(models.Factura.id == factura_id)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    factura = query.first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)
    return templates.TemplateResponse("facturas/detalle.html", {
        "request": request,
        "factura": factura,
        "metodos_pago": METODOS_PAGO,
        "msg": msg,
        "error": error,
    })


# ── Registrar cobro ──────────────────────────────────────────────────────────

@router.post("/{factura_id}/cobrar")
def registrar_cobro(
    factura_id: int,
    request: Request,
    monto: float = Form(...),
    fecha_cobro: str = Form(...),
    metodo_pago: str = Form("EFECTIVO"),
    comprobante: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    if monto <= 0:
        return RedirectResponse(f"/facturas/{factura_id}/detalle?error=El+monto+debe+ser+mayor+a+cero", status_code=303)

    try:
        query = db.query(models.Factura).filter(models.Factura.id == factura_id)
        if local_id is not None:
            query = query.filter(models.Factura.local_id == local_id)
        factura = query.with_for_update().first()
        if not factura:
            return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)
        if factura.estado == "PAGADO":
            return RedirectResponse(f"/facturas/{factura_id}/detalle?error=La+factura+ya+está+completamente+cobrada", status_code=303)

        monto_aplicar = min(monto, factura.monto_pendiente)
        cobro = models.PagoFactura(
            factura_id=factura_id,
            monto=monto_aplicar,
            fecha_cobro=datetime.strptime(fecha_cobro, "%Y-%m-%d"),
            metodo_pago=metodo_pago,
            comprobante=comprobante.strip(),
            notas=notas.strip(),
        )
        cobro.local_id = local_id
        db.add(cobro)
        factura.monto_cobrado = round(factura.monto_cobrado + monto_aplicar, 2)
        _actualizar_estado(factura)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(f"/facturas/{factura_id}/detalle?error=Error+al+registrar+el+cobro", status_code=303)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "cobro_factura", cobro.id,
              f"Cobro registrado: ${monto_aplicar:,.2f} a factura #{factura_id}", ip)

    return RedirectResponse(f"/facturas/{factura_id}/detalle?msg=Cobro+registrado+correctamente", status_code=303)


# ── Eliminar cobro ───────────────────────────────────────────────────────────

@router.post("/{factura_id}/cobros/{cobro_id}/eliminar")
def eliminar_cobro(factura_id: int, cobro_id: int, request: Request,
                   db: Session = Depends(get_db),
                   current_user: models.Usuario = Depends(require_auth)):
    local_id = get_local_id(request)
    query = db.query(models.PagoFactura).filter(
        models.PagoFactura.id == cobro_id,
        models.PagoFactura.factura_id == factura_id,
    )
    if local_id is not None:
        query = query.filter(models.PagoFactura.local_id == local_id)
    cobro = query.first()
    if not cobro:
        return RedirectResponse(f"/facturas/{factura_id}/detalle?error=Cobro+no+encontrado", status_code=303)
    factura = cobro.factura
    monto_cobro = cobro.monto
    factura.monto_cobrado = max(0.0, round(factura.monto_cobrado - monto_cobro, 2))
    db.delete(cobro)
    _actualizar_estado(factura)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "cobro_factura", cobro_id,
              f"Cobro eliminado: ${monto_cobro:,.2f} de factura #{factura_id}", ip)

    return RedirectResponse(f"/facturas/{factura_id}/detalle?msg=Cobro+eliminado+correctamente", status_code=303)


# ── Exportar Excel ───────────────────────────────────────────────────────────

@router.get("/exportar")
def exportar_facturas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    buscar: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    vencidas: str = None,
):
    from utils.excel import generate_excel

    local_id = get_local_id(request)
    query = db.query(models.Factura)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    if estado:
        query = query.filter(models.Factura.estado == estado)
    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.Factura.cliente_nombre.ilike(term) |
            models.Factura.numero_factura.ilike(term) |
            models.Factura.concepto.ilike(term) |
            models.Factura.cliente_documento.ilike(term)
        )
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
            query = query.filter(models.Factura.fecha_emision >= fd)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Factura.fecha_emision <= fh)
        except ValueError:
            pass
    if vencidas == "1":
        query = query.filter(
            models.Factura.fecha_vencimiento < datetime.now(),
            models.Factura.estado != "PAGADO",
        )

    facturas = query.order_by(models.Factura.fecha_vencimiento.asc().nullsfirst(),
                              models.Factura.created_at.desc()).all()

    headers = ["N° Factura", "Cliente", "Empresa", "Documento", "Concepto",
               "Emision", "Vencimiento", "Total", "Cobrado", "Pendiente", "Estado"]
    rows = []
    for f in facturas:
        estado_txt = "VENCIDA" if f.esta_vencida else f.estado
        rows.append([
            f.numero_factura,
            f.cliente_nombre,
            f.cliente_empresa or "",
            f.cliente_documento or "",
            f.concepto,
            f.fecha_emision.strftime("%d/%m/%Y") if f.fecha_emision else "",
            f.fecha_vencimiento.strftime("%d/%m/%Y") if f.fecha_vencimiento else "",
            f.monto_total,
            f.monto_cobrado,
            f.monto_pendiente,
            estado_txt,
        ])

    output = generate_excel(
        "Listado de Facturas", headers, rows,
        col_widths=[14, 22, 18, 16, 28, 14, 14, 14, 14, 14, 12],
        money_cols=[7, 8, 9],
    )
    filename = f"facturas_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Reporte HTML ─────────────────────────────────────────────────────────────

@router.get("/reporte")
def reporte_facturas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Factura)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Factura.fecha_emision >= fd, models.Factura.fecha_emision <= fh)
    except ValueError:
        pass

    if estado:
        query = query.filter(models.Factura.estado == estado)

    facturas = query.order_by(models.Factura.fecha_vencimiento.asc().nullsfirst()).all()

    total_facturado = sum(f.monto_total   for f in facturas)
    total_cobrado   = sum(f.monto_cobrado for f in facturas)
    total_pend      = sum(f.monto_pendiente for f in facturas)
    total_venc      = sum(1 for f in facturas if f.esta_vencida)

    return templates.TemplateResponse("facturas/reporte.html", {
        "request":       request,
        "facturas":      facturas,
        "fecha_desde":   fecha_desde,
        "fecha_hasta":   fecha_hasta,
        "estado":        estado or "",
        "total_facturado": total_facturado,
        "total_cobrado":   total_cobrado,
        "total_pend":      total_pend,
        "total_venc":      total_venc,
        "fecha_reporte": datetime.now(),
    })


# ── Reporte PDF ───────────────────────────────────────────────────────────────

@router.get("/reporte/pdf")
def reporte_facturas_pdf(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    from utils.pdf import generate_report_pdf

    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Factura)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Factura.fecha_emision >= fd, models.Factura.fecha_emision <= fh)
    except ValueError:
        pass
    if estado:
        query = query.filter(models.Factura.estado == estado)

    facturas = query.order_by(models.Factura.fecha_vencimiento.asc().nullsfirst()).all()

    headers = ["N° Factura", "Cliente", "Documento", "Concepto", "Emisión", "Vencimiento",
               "Total", "Cobrado", "Pendiente", "Estado"]
    rows = []
    for f in facturas:
        estado_txt = "VENCIDA" if f.esta_vencida else f.estado
        rows.append([
            f.numero_factura,
            f.cliente_nombre[:28],
            f.cliente_documento or "—",
            f.concepto[:30],
            f.fecha_emision.strftime("%d/%m/%Y"),
            f.fecha_vencimiento.strftime("%d/%m/%Y") if f.fecha_vencimiento else "—",
            f"${f.monto_total:,.2f}",
            f"${f.monto_cobrado:,.2f}",
            f"${f.monto_pendiente:,.2f}",
            estado_txt,
        ])

    totals_row = ["", "", "", "TOTAL", "", "",
                  f"${sum(f.monto_total for f in facturas):,.2f}",
                  f"${sum(f.monto_cobrado for f in facturas):,.2f}",
                  f"${sum(f.monto_pendiente for f in facturas):,.2f}", ""]

    buffer = generate_report_pdf(
        title="TechStock — Reporte de Facturas / Cuentas por Cobrar",
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        headers=headers,
        rows=rows,
        totals_row=totals_row,
        col_widths_cm=[2.4, 4.5, 2.5, 4.5, 2.2, 2.2, 2.5, 2.5, 2.5, 2.2],
        estado_col_index=9,
    )

    filename = f"reporte_facturas_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={filename}"})


# ── Eliminar factura ─────────────────────────────────────────────────────────

@router.post("/{factura_id}/eliminar")
def eliminar_factura(factura_id: int, request: Request,
                     db: Session = Depends(get_db),
                     current_user: models.Usuario = Depends(require_auth)):
    local_id = get_local_id(request)
    query = db.query(models.Factura).filter(models.Factura.id == factura_id)
    if local_id is not None:
        query = query.filter(models.Factura.local_id == local_id)
    factura = query.first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)

    numero = factura.numero_factura
    factura.estado = "ANULADO"
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "factura", factura_id,
              f"Factura anulada: {numero}", ip)

    return RedirectResponse("/facturas?msg=Factura+eliminada+correctamente", status_code=303)
