from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, date, timedelta
from database import get_db
from templates_config import templates
from auth import require_auth, log_audit, get_local_id
from utils.queries import proveedores_activos, acreedores_activos
import models

router = APIRouter(prefix="/deudas", tags=["deudas"])

from utils.constants import METODOS_PAGO, TIPOS_ACREEDOR


from utils.financial import actualizar_estado_pago as _actualizar_estado_pago


def _actualizar_estado(deuda: models.Deuda):
    """Recalcula el estado de la deuda según montos."""
    _actualizar_estado_pago(deuda, "monto_pagado")


# ── Lista ────────────────────────────────────────────────────────────────────

@router.get("")
def lista_deudas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    acreedor_tipo: str = None,
    buscar: str = None,
    msg: str = None,
    error: str = None,
):
    local_id = get_local_id(request)
    query = db.query(models.Deuda)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    if estado:
        query = query.filter(models.Deuda.estado == estado)
    if acreedor_tipo:
        query = query.filter(models.Deuda.acreedor_tipo == acreedor_tipo)
    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.Deuda.acreedor_nombre.ilike(term)
            | models.Deuda.concepto.ilike(term)
        )
    deudas = query.order_by(models.Deuda.fecha_vencimiento.asc().nullsfirst(),
                            models.Deuda.created_at.desc()).all()

    total_deuda = sum(d.monto_total for d in deudas)
    total_pagado = sum(d.monto_pagado for d in deudas)
    total_pendiente = sum(d.monto_pendiente for d in deudas if d.estado != "PAGADO")
    total_vencidas = sum(1 for d in deudas if d.esta_vencida)

    return templates.TemplateResponse("deudas/lista.html", {
        "request": request,
        "deudas": deudas,
        "total_deuda": total_deuda,
        "total_pagado": total_pagado,
        "total_pendiente": total_pendiente,
        "total_vencidas": total_vencidas,
        "estado": estado or "",
        "acreedor_tipo": acreedor_tipo or "",
        "buscar": buscar or "",
        "tipos_acreedor": TIPOS_ACREEDOR,
        "msg": msg,
        "error": error,
    })


# ── Nueva deuda ──────────────────────────────────────────────────────────────

@router.get("/nueva")
def nueva_deuda_form(request: Request, db: Session = Depends(get_db)):
    local_id = get_local_id(request)
    proveedores = proveedores_activos(db, local_id=local_id)
    acreedores = acreedores_activos(db, local_id=local_id)
    return templates.TemplateResponse("deudas/form.html", {
        "request": request,
        "deuda": None,
        "proveedores": proveedores,
        "acreedores": acreedores,
        "tipos_acreedor": TIPOS_ACREEDOR,
        "accion": "Nueva",
        "error": None,
    })


@router.post("/nueva")
def crear_deuda(
    request: Request,
    concepto: str = Form(...),
    acreedor_nombre: str = Form(...),
    acreedor_empresa: str = Form(""),
    acreedor_tipo: str = Form("OTRO"),
    acreedor_id: str = Form(""),
    proveedor_id: str = Form(""),
    monto_total: float = Form(...),
    fecha_deuda: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    prov_id = int(proveedor_id) if proveedor_id.strip() else None
    acr_id = int(acreedor_id) if acreedor_id.strip() else None
    fec_deuda = datetime.strptime(fecha_deuda, "%Y-%m-%d") if fecha_deuda else datetime.now()
    fec_venc = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None

    deuda = models.Deuda(
        concepto=concepto.strip(),
        acreedor_nombre=acreedor_nombre.strip(),
        acreedor_empresa=acreedor_empresa.strip(),
        acreedor_tipo=acreedor_tipo,
        acreedor_id=acr_id,
        proveedor_id=prov_id,
        monto_total=monto_total,
        fecha_deuda=fec_deuda,
        fecha_vencimiento=fec_venc,
        notas=notas.strip(),
    )
    deuda.local_id = get_local_id(request)
    db.add(deuda)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "deuda", deuda.id,
              f"Deuda creada: {concepto.strip()} por ${monto_total:,.2f}", ip)

    return RedirectResponse("/deudas?msg=Deuda+registrada+correctamente", status_code=303)


# ── Editar ───────────────────────────────────────────────────────────────────

@router.get("/{deuda_id}/editar")
def editar_deuda_form(deuda_id: int, request: Request, db: Session = Depends(get_db)):
    local_id = get_local_id(request)
    query = db.query(models.Deuda).filter(models.Deuda.id == deuda_id)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    deuda = query.first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)
    proveedores = proveedores_activos(db, local_id=local_id)
    acreedores = acreedores_activos(db, local_id=local_id)
    return templates.TemplateResponse("deudas/form.html", {
        "request": request,
        "deuda": deuda,
        "proveedores": proveedores,
        "acreedores": acreedores,
        "tipos_acreedor": TIPOS_ACREEDOR,
        "accion": "Editar",
        "error": None,
    })


@router.post("/{deuda_id}/editar")
def actualizar_deuda(
    deuda_id: int,
    request: Request,
    concepto: str = Form(...),
    acreedor_nombre: str = Form(...),
    acreedor_empresa: str = Form(""),
    acreedor_tipo: str = Form("OTRO"),
    acreedor_id: str = Form(""),
    proveedor_id: str = Form(""),
    monto_total: float = Form(...),
    fecha_deuda: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Deuda).filter(models.Deuda.id == deuda_id)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    deuda = query.first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)

    deuda.concepto = concepto.strip()
    deuda.acreedor_nombre = acreedor_nombre.strip()
    deuda.acreedor_empresa = acreedor_empresa.strip()
    deuda.acreedor_tipo = acreedor_tipo
    deuda.acreedor_id = int(acreedor_id) if acreedor_id.strip() else None
    deuda.proveedor_id = int(proveedor_id) if proveedor_id.strip() else None
    deuda.monto_total = monto_total
    deuda.fecha_deuda = datetime.strptime(fecha_deuda, "%Y-%m-%d") if fecha_deuda else deuda.fecha_deuda
    deuda.fecha_vencimiento = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None
    deuda.notas = notas.strip()
    _actualizar_estado(deuda)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "deuda", deuda.id,
              f"Deuda actualizada: {concepto.strip()}", ip)

    return RedirectResponse(f"/deudas/{deuda_id}/detalle?msg=Deuda+actualizada+correctamente", status_code=303)


# ── Detalle + historial de pagos ─────────────────────────────────────────────

@router.get("/{deuda_id}/detalle")
def detalle_deuda(deuda_id: int, request: Request, db: Session = Depends(get_db),
                  msg: str = None, error: str = None):
    local_id = get_local_id(request)
    query = db.query(models.Deuda).options(
        joinedload(models.Deuda.pagos)
    ).filter(models.Deuda.id == deuda_id)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    deuda = query.first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)
    return templates.TemplateResponse("deudas/detalle.html", {
        "request": request,
        "deuda": deuda,
        "metodos_pago": METODOS_PAGO,
        "msg": msg,
        "error": error,
    })


# ── Registrar pago ───────────────────────────────────────────────────────────

@router.post("/{deuda_id}/pagar")
def registrar_pago(
    deuda_id: int,
    request: Request,
    monto: float = Form(...),
    fecha_pago: str = Form(...),
    metodo_pago: str = Form("EFECTIVO"),
    comprobante: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    if monto <= 0:
        return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=El+monto+debe+ser+mayor+a+cero", status_code=303)

    try:
        query = db.query(models.Deuda).filter(models.Deuda.id == deuda_id)
        if local_id is not None:
            query = query.filter(models.Deuda.local_id == local_id)
        deuda = query.with_for_update().first()
        if not deuda:
            return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)
        if deuda.estado == "PAGADO":
            return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=La+deuda+ya+está+completamente+pagada", status_code=303)

        monto_aplicar = min(monto, deuda.monto_pendiente)
        pago = models.PagoDeuda(
            deuda_id=deuda_id,
            monto=monto_aplicar,
            fecha_pago=datetime.strptime(fecha_pago, "%Y-%m-%d"),
            metodo_pago=metodo_pago,
            comprobante=comprobante.strip(),
            notas=notas.strip(),
        )
        pago.local_id = local_id
        db.add(pago)
        deuda.monto_pagado = round(deuda.monto_pagado + monto_aplicar, 2)
        _actualizar_estado(deuda)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=Error+al+registrar+el+pago", status_code=303)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "pago_deuda", pago.id,
              f"Pago registrado: ${monto_aplicar:,.2f} a deuda #{deuda_id}", ip)

    return RedirectResponse(f"/deudas/{deuda_id}/detalle?msg=Pago+registrado+correctamente", status_code=303)


# ── Eliminar pago ────────────────────────────────────────────────────────────

@router.post("/{deuda_id}/pagos/{pago_id}/eliminar")
def eliminar_pago(deuda_id: int, pago_id: int, request: Request,
                  db: Session = Depends(get_db),
                  current_user: models.Usuario = Depends(require_auth)):
    local_id = get_local_id(request)
    pago_query = db.query(models.PagoDeuda).filter(
        models.PagoDeuda.id == pago_id,
        models.PagoDeuda.deuda_id == deuda_id,
    )
    if local_id is not None:
        pago_query = pago_query.filter(models.PagoDeuda.local_id == local_id)
    pago = pago_query.first()
    if not pago:
        return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=Pago+no+encontrado", status_code=303)
    deuda = pago.deuda
    monto_pago = pago.monto
    deuda.monto_pagado = max(0.0, round(deuda.monto_pagado - monto_pago, 2))
    db.delete(pago)
    _actualizar_estado(deuda)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "pago_deuda", pago_id,
              f"Pago eliminado: ${monto_pago:,.2f} de deuda #{deuda_id}", ip)

    return RedirectResponse(f"/deudas/{deuda_id}/detalle?msg=Pago+eliminado+correctamente", status_code=303)


# ── Exportar Excel ───────────────────────────────────────────────────────────

@router.get("/exportar")
def exportar_deudas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    acreedor_tipo: str = None,
    buscar: str = None,
):
    from utils.excel import generate_excel

    local_id = get_local_id(request)
    query = db.query(models.Deuda)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    if estado:
        query = query.filter(models.Deuda.estado == estado)
    if acreedor_tipo:
        query = query.filter(models.Deuda.acreedor_tipo == acreedor_tipo)
    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.Deuda.acreedor_nombre.ilike(term)
            | models.Deuda.concepto.ilike(term)
        )
    deudas = query.order_by(models.Deuda.fecha_vencimiento.asc().nullsfirst(),
                            models.Deuda.created_at.desc()).all()

    headers = ["Acreedor", "Empresa", "Tipo", "Concepto", "Fecha Deuda",
               "Vencimiento", "Total", "Pagado", "Pendiente", "Estado"]
    rows = []
    for d in deudas:
        estado_txt = "VENCIDA" if d.esta_vencida else d.estado
        rows.append([
            d.acreedor_nombre,
            d.acreedor_empresa or "",
            d.acreedor_tipo,
            d.concepto,
            d.fecha_deuda.strftime("%d/%m/%Y") if d.fecha_deuda else "",
            d.fecha_vencimiento.strftime("%d/%m/%Y") if d.fecha_vencimiento else "",
            d.monto_total,
            d.monto_pagado,
            d.monto_pendiente,
            estado_txt,
        ])

    output = generate_excel(
        "Listado de Deudas", headers, rows,
        col_widths=[22, 18, 14, 28, 14, 14, 14, 14, 14, 12],
        money_cols=[6, 7, 8],
    )
    filename = f"deudas_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Reporte HTML ─────────────────────────────────────────────────────────────

@router.get("/reporte")
def reporte_deudas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    acreedor_tipo: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Deuda)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Deuda.fecha_deuda >= fd, models.Deuda.fecha_deuda <= fh)
    except ValueError:
        pass

    if estado:
        query = query.filter(models.Deuda.estado == estado)
    if acreedor_tipo:
        query = query.filter(models.Deuda.acreedor_tipo == acreedor_tipo)

    deudas = query.order_by(models.Deuda.fecha_vencimiento.asc().nullsfirst()).all()
    ahora  = datetime.now()

    total_deuda   = sum(d.monto_total for d in deudas)
    total_pagado  = sum(d.monto_pagado for d in deudas)
    total_pend    = sum(d.monto_pendiente for d in deudas)
    total_venc    = sum(1 for d in deudas if d.esta_vencida)

    return templates.TemplateResponse("deudas/reporte.html", {
        "request":       request,
        "deudas":        deudas,
        "fecha_desde":   fecha_desde,
        "fecha_hasta":   fecha_hasta,
        "estado":        estado or "",
        "acreedor_tipo": acreedor_tipo or "",
        "tipos_acreedor": TIPOS_ACREEDOR,
        "total_deuda":   total_deuda,
        "total_pagado":  total_pagado,
        "total_pend":    total_pend,
        "total_venc":    total_venc,
        "fecha_reporte": datetime.now(),
    })


# ── Reporte PDF ───────────────────────────────────────────────────────────────

@router.get("/reporte/pdf")
def reporte_deudas_pdf(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    acreedor_tipo: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    from utils.pdf import generate_report_pdf

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Deuda)
    local_id = get_local_id(request)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Deuda.fecha_deuda >= fd, models.Deuda.fecha_deuda <= fh)
    except ValueError:
        pass
    if estado:
        query = query.filter(models.Deuda.estado == estado)
    if acreedor_tipo:
        query = query.filter(models.Deuda.acreedor_tipo == acreedor_tipo)

    deudas = query.order_by(models.Deuda.fecha_vencimiento.asc().nullsfirst()).all()

    headers = ["Acreedor", "Tipo", "Concepto", "Fecha", "Vencimiento", "Total", "Pagado", "Pendiente", "Estado"]
    rows = []
    for d in deudas:
        estado_txt = "VENCIDA" if d.esta_vencida else d.estado
        rows.append([
            d.acreedor_nombre[:30],
            d.acreedor_tipo,
            d.concepto[:35],
            d.fecha_deuda.strftime("%d/%m/%Y"),
            d.fecha_vencimiento.strftime("%d/%m/%Y") if d.fecha_vencimiento else "—",
            f"${d.monto_total:,.2f}",
            f"${d.monto_pagado:,.2f}",
            f"${d.monto_pendiente:,.2f}",
            estado_txt,
        ])

    totals_row = ["", "", "TOTAL", "", "",
                  f"${sum(d.monto_total for d in deudas):,.2f}",
                  f"${sum(d.monto_pagado for d in deudas):,.2f}",
                  f"${sum(d.monto_pendiente for d in deudas):,.2f}", ""]

    buffer = generate_report_pdf(
        title="TechStock — Reporte de Deudas / Cuentas por Pagar",
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        headers=headers,
        rows=rows,
        totals_row=totals_row,
        col_widths_cm=[4.5, 2, 5.5, 2.3, 2.3, 2.5, 2.5, 2.5, 2.2],
        estado_col_index=8,
    )

    filename = f"reporte_deudas_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={filename}"})


# ── Eliminar deuda ───────────────────────────────────────────────────────────

@router.post("/{deuda_id}/eliminar")
def eliminar_deuda(deuda_id: int, request: Request,
                   db: Session = Depends(get_db),
                   current_user: models.Usuario = Depends(require_auth)):
    local_id = get_local_id(request)
    query = db.query(models.Deuda).filter(models.Deuda.id == deuda_id)
    if local_id is not None:
        query = query.filter(models.Deuda.local_id == local_id)
    deuda = query.first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)

    concepto = deuda.concepto
    deuda.estado = "ANULADO"
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "deuda", deuda_id,
              f"Deuda anulada: {concepto}", ip)

    return RedirectResponse("/deudas?msg=Deuda+eliminada+correctamente", status_code=303)
