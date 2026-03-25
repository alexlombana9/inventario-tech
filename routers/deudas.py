from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from database import get_db
from templates_config import templates
import models
import io

router = APIRouter(prefix="/deudas", tags=["deudas"])

METODOS_PAGO = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CHEQUE"]
TIPOS_ACREEDOR = ["PROVEEDOR", "BANCO", "PERSONA", "OTRO"]


def _actualizar_estado(deuda: models.Deuda):
    """Recalcula el estado de la deuda según montos."""
    if deuda.monto_pagado >= deuda.monto_total:
        deuda.estado = "PAGADO"
    elif deuda.monto_pagado > 0:
        deuda.estado = "PARCIAL"
    else:
        deuda.estado = "PENDIENTE"


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
    query = db.query(models.Deuda)
    if estado:
        query = query.filter(models.Deuda.estado == estado)
    if acreedor_tipo:
        query = query.filter(models.Deuda.acreedor_tipo == acreedor_tipo)
    if buscar:
        query = query.filter(models.Deuda.acreedor_nombre.ilike(f"%{buscar}%"))
    deudas = query.order_by(models.Deuda.fecha_vencimiento.asc().nullsfirst(),
                            models.Deuda.created_at.desc()).all()

    total_pendiente = sum(d.monto_pendiente for d in deudas if d.estado != "PAGADO")
    total_vencidas = sum(1 for d in deudas if d.esta_vencida)

    return templates.TemplateResponse("deudas/lista.html", {
        "request": request,
        "deudas": deudas,
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
    proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).order_by(models.Proveedor.nombre).all()
    acreedores = db.query(models.Acreedor).filter(models.Acreedor.activo == True).order_by(models.Acreedor.nombre).all()
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
    concepto: str = Form(...),
    acreedor_nombre: str = Form(...),
    acreedor_tipo: str = Form("OTRO"),
    acreedor_id: str = Form(""),
    proveedor_id: str = Form(""),
    monto_total: float = Form(...),
    fecha_deuda: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    prov_id = int(proveedor_id) if proveedor_id.strip() else None
    acr_id = int(acreedor_id) if acreedor_id.strip() else None
    fec_deuda = datetime.strptime(fecha_deuda, "%Y-%m-%d") if fecha_deuda else datetime.now()
    fec_venc = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None

    deuda = models.Deuda(
        concepto=concepto.strip(),
        acreedor_nombre=acreedor_nombre.strip(),
        acreedor_tipo=acreedor_tipo,
        acreedor_id=acr_id,
        proveedor_id=prov_id,
        monto_total=monto_total,
        fecha_deuda=fec_deuda,
        fecha_vencimiento=fec_venc,
        notas=notas.strip(),
    )
    db.add(deuda)
    db.commit()
    return RedirectResponse("/deudas?msg=Deuda+registrada+correctamente", status_code=303)


# ── Editar ───────────────────────────────────────────────────────────────────

@router.get("/{deuda_id}/editar")
def editar_deuda_form(deuda_id: int, request: Request, db: Session = Depends(get_db)):
    deuda = db.query(models.Deuda).filter(models.Deuda.id == deuda_id).first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)
    proveedores = db.query(models.Proveedor).filter(models.Proveedor.activo == True).order_by(models.Proveedor.nombre).all()
    acreedores = db.query(models.Acreedor).filter(models.Acreedor.activo == True).order_by(models.Acreedor.nombre).all()
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
    concepto: str = Form(...),
    acreedor_nombre: str = Form(...),
    acreedor_tipo: str = Form("OTRO"),
    acreedor_id: str = Form(""),
    proveedor_id: str = Form(""),
    monto_total: float = Form(...),
    fecha_deuda: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    deuda = db.query(models.Deuda).filter(models.Deuda.id == deuda_id).first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)

    deuda.concepto = concepto.strip()
    deuda.acreedor_nombre = acreedor_nombre.strip()
    deuda.acreedor_tipo = acreedor_tipo
    deuda.acreedor_id = int(acreedor_id) if acreedor_id.strip() else None
    deuda.proveedor_id = int(proveedor_id) if proveedor_id.strip() else None
    deuda.monto_total = monto_total
    deuda.fecha_deuda = datetime.strptime(fecha_deuda, "%Y-%m-%d") if fecha_deuda else deuda.fecha_deuda
    deuda.fecha_vencimiento = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None
    deuda.notas = notas.strip()
    _actualizar_estado(deuda)
    db.commit()
    return RedirectResponse(f"/deudas/{deuda_id}/detalle?msg=Deuda+actualizada+correctamente", status_code=303)


# ── Detalle + historial de pagos ─────────────────────────────────────────────

@router.get("/{deuda_id}/detalle")
def detalle_deuda(deuda_id: int, request: Request, db: Session = Depends(get_db),
                  msg: str = None, error: str = None):
    deuda = db.query(models.Deuda).filter(models.Deuda.id == deuda_id).first()
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
    monto: float = Form(...),
    fecha_pago: str = Form(...),
    metodo_pago: str = Form("EFECTIVO"),
    comprobante: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    deuda = db.query(models.Deuda).filter(models.Deuda.id == deuda_id).first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)
    if deuda.estado == "PAGADO":
        return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=La+deuda+ya+está+completamente+pagada", status_code=303)
    if monto <= 0:
        return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=El+monto+debe+ser+mayor+a+cero", status_code=303)

    monto_aplicar = min(monto, deuda.monto_pendiente)
    pago = models.PagoDeuda(
        deuda_id=deuda_id,
        monto=monto_aplicar,
        fecha_pago=datetime.strptime(fecha_pago, "%Y-%m-%d"),
        metodo_pago=metodo_pago,
        comprobante=comprobante.strip(),
        notas=notas.strip(),
    )
    db.add(pago)
    deuda.monto_pagado = round(deuda.monto_pagado + monto_aplicar, 2)
    _actualizar_estado(deuda)
    db.commit()
    return RedirectResponse(f"/deudas/{deuda_id}/detalle?msg=Pago+registrado+correctamente", status_code=303)


# ── Eliminar pago ────────────────────────────────────────────────────────────

@router.post("/{deuda_id}/pagos/{pago_id}/eliminar")
def eliminar_pago(deuda_id: int, pago_id: int, db: Session = Depends(get_db)):
    pago = db.query(models.PagoDeuda).filter(
        models.PagoDeuda.id == pago_id,
        models.PagoDeuda.deuda_id == deuda_id,
    ).first()
    if not pago:
        return RedirectResponse(f"/deudas/{deuda_id}/detalle?error=Pago+no+encontrado", status_code=303)
    deuda = pago.deuda
    deuda.monto_pagado = max(0.0, round(deuda.monto_pagado - pago.monto, 2))
    db.delete(pago)
    _actualizar_estado(deuda)
    db.commit()
    return RedirectResponse(f"/deudas/{deuda_id}/detalle?msg=Pago+eliminado+correctamente", status_code=303)


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
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Deuda)
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
    db: Session = Depends(get_db),
    estado: str = None,
    acreedor_tipo: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Deuda)
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

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                             rightMargin=1.5*cm, leftMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=15, alignment=TA_CENTER, spaceAfter=0.2*cm)
    sub_style   = ParagraphStyle('Sub', parent=styles['Normal'],
                                  fontSize=8, alignment=TA_CENTER, spaceAfter=0.4*cm,
                                  textColor=colors.grey)

    elements.append(Paragraph("TechStock — Reporte de Deudas / Cuentas por Pagar", title_style))
    elements.append(Paragraph(
        f"Período: {fecha_desde} al {fecha_hasta}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))
    elements.append(Spacer(1, 0.3*cm))

    header = ["Acreedor", "Tipo", "Concepto", "Fecha", "Vencimiento", "Total", "Pagado", "Pendiente", "Estado"]
    data = [header]

    for d in deudas:
        estado_txt = "VENCIDA" if d.esta_vencida else d.estado
        data.append([
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

    total_pend = sum(d.monto_pendiente for d in deudas)
    data.append(["", "", "TOTAL", "", "", f"${sum(d.monto_total for d in deudas):,.2f}",
                  f"${sum(d.monto_pagado for d in deudas):,.2f}", f"${total_pend:,.2f}", ""])

    col_widths = [4.5*cm, 2*cm, 5.5*cm, 2.3*cm, 2.3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.2*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    ESTADO_COLORS = {
        "PENDIENTE": colors.HexColor('#fff3cd'),
        "PARCIAL":   colors.HexColor('#cfe2ff'),
        "PAGADO":    colors.HexColor('#d1e7dd'),
        "VENCIDA":   colors.HexColor('#f8d7da'),
    }

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 8),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN',      (0, 1), (2, -1), 'LEFT'),
        ('FONTSIZE',   (0, 1), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID',       (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
    ])

    for i, d in enumerate(deudas, start=1):
        estado_txt = "VENCIDA" if d.esta_vencida else d.estado
        color = ESTADO_COLORS.get(estado_txt)
        if color:
            style.add('BACKGROUND', (8, i), (8, i), color)

    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    filename = f"reporte_deudas_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={filename}"})


# ── Eliminar deuda ───────────────────────────────────────────────────────────

@router.post("/{deuda_id}/eliminar")
def eliminar_deuda(deuda_id: int, db: Session = Depends(get_db)):
    deuda = db.query(models.Deuda).filter(models.Deuda.id == deuda_id).first()
    if not deuda:
        return RedirectResponse("/deudas?error=Deuda+no+encontrada", status_code=303)
    db.delete(deuda)
    db.commit()
    return RedirectResponse("/deudas?msg=Deuda+eliminada+correctamente", status_code=303)
