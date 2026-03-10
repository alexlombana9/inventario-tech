from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from database import get_db
from templates_config import templates
import models
import io

router = APIRouter(prefix="/facturas", tags=["facturas"])

METODOS_PAGO = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CHEQUE"]


def _actualizar_estado(factura: models.Factura):
    """Recalcula el estado de la factura según montos cobrados."""
    if factura.monto_cobrado >= factura.monto_total:
        factura.estado = "PAGADO"
    elif factura.monto_cobrado > 0:
        factura.estado = "PARCIAL"
    else:
        factura.estado = "PENDIENTE"


def _siguiente_numero(db: Session) -> str:
    """Genera el próximo número de factura correlativo."""
    ultimo = db.query(models.Factura).order_by(models.Factura.id.desc()).first()
    if not ultimo:
        return "FAC-0001"
    try:
        num = int(ultimo.numero_factura.split("-")[-1]) + 1
        return f"FAC-{num:04d}"
    except (ValueError, IndexError):
        return f"FAC-{ultimo.id + 1:04d}"


# ── Lista ────────────────────────────────────────────────────────────────────

@router.get("")
def lista_facturas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    buscar: str = None,
    msg: str = None,
    error: str = None,
):
    query = db.query(models.Factura)
    if estado:
        query = query.filter(models.Factura.estado == estado)
    if buscar:
        query = query.filter(
            models.Factura.cliente_nombre.ilike(f"%{buscar}%") |
            models.Factura.numero_factura.ilike(f"%{buscar}%")
        )
    facturas = query.order_by(models.Factura.fecha_vencimiento.asc().nullsfirst(),
                              models.Factura.created_at.desc()).all()

    total_por_cobrar = sum(f.monto_pendiente for f in facturas if f.estado != "PAGADO")
    total_vencidas = sum(1 for f in facturas if f.esta_vencida)

    return templates.TemplateResponse("facturas/lista.html", {
        "request": request,
        "facturas": facturas,
        "total_por_cobrar": total_por_cobrar,
        "total_vencidas": total_vencidas,
        "estado": estado or "",
        "buscar": buscar or "",
        "msg": msg,
        "error": error,
    })


# ── Nueva factura ────────────────────────────────────────────────────────────

@router.get("/nueva")
def nueva_factura_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("facturas/form.html", {
        "request": request,
        "factura": None,
        "numero_sugerido": _siguiente_numero(db),
        "accion": "Nueva",
        "error": None,
    })


@router.post("/nueva")
def crear_factura(
    numero_factura: str = Form(...),
    cliente_nombre: str = Form(...),
    cliente_documento: str = Form(""),
    cliente_telefono: str = Form(""),
    cliente_email: str = Form(""),
    concepto: str = Form(...),
    monto_total: float = Form(...),
    fecha_emision: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    existe = db.query(models.Factura).filter(
        models.Factura.numero_factura == numero_factura.strip()
    ).first()
    if existe:
        return templates.TemplateResponse("facturas/form.html", {
            "request": None,
            "factura": None,
            "numero_sugerido": numero_factura,
            "accion": "Nueva",
            "error": f"Ya existe una factura con el número '{numero_factura}'.",
        })

    fec_emision = datetime.strptime(fecha_emision, "%Y-%m-%d") if fecha_emision else datetime.now()
    fec_venc = datetime.strptime(fecha_vencimiento, "%Y-%m-%d") if fecha_vencimiento.strip() else None

    factura = models.Factura(
        numero_factura=numero_factura.strip(),
        cliente_nombre=cliente_nombre.strip(),
        cliente_documento=cliente_documento.strip(),
        cliente_telefono=cliente_telefono.strip(),
        cliente_email=cliente_email.strip(),
        concepto=concepto.strip(),
        monto_total=monto_total,
        fecha_emision=fec_emision,
        fecha_vencimiento=fec_venc,
        notas=notas.strip(),
    )
    db.add(factura)
    db.commit()
    return RedirectResponse("/facturas?msg=Factura+creada+correctamente", status_code=303)


# ── Editar ───────────────────────────────────────────────────────────────────

@router.get("/{factura_id}/editar")
def editar_factura_form(factura_id: int, request: Request, db: Session = Depends(get_db)):
    factura = db.query(models.Factura).filter(models.Factura.id == factura_id).first()
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
    numero_factura: str = Form(...),
    cliente_nombre: str = Form(...),
    cliente_documento: str = Form(""),
    cliente_telefono: str = Form(""),
    cliente_email: str = Form(""),
    concepto: str = Form(...),
    monto_total: float = Form(...),
    fecha_emision: str = Form(...),
    fecha_vencimiento: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    factura = db.query(models.Factura).filter(models.Factura.id == factura_id).first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)

    duplicado = db.query(models.Factura).filter(
        models.Factura.numero_factura == numero_factura.strip(),
        models.Factura.id != factura_id,
    ).first()
    if duplicado:
        return RedirectResponse(
            f"/facturas/{factura_id}/editar?error=Número+de+factura+ya+en+uso",
            status_code=303,
        )

    factura.numero_factura = numero_factura.strip()
    factura.cliente_nombre = cliente_nombre.strip()
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
    return RedirectResponse(f"/facturas/{factura_id}/detalle?msg=Factura+actualizada+correctamente", status_code=303)


# ── Detalle + historial de cobros ────────────────────────────────────────────

@router.get("/{factura_id}/detalle")
def detalle_factura(factura_id: int, request: Request, db: Session = Depends(get_db),
                    msg: str = None, error: str = None):
    factura = db.query(models.Factura).filter(models.Factura.id == factura_id).first()
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
    monto: float = Form(...),
    fecha_cobro: str = Form(...),
    metodo_pago: str = Form("EFECTIVO"),
    comprobante: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    factura = db.query(models.Factura).filter(models.Factura.id == factura_id).first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)
    if factura.estado == "PAGADO":
        return RedirectResponse(f"/facturas/{factura_id}/detalle?error=La+factura+ya+está+completamente+cobrada", status_code=303)
    if monto <= 0:
        return RedirectResponse(f"/facturas/{factura_id}/detalle?error=El+monto+debe+ser+mayor+a+cero", status_code=303)

    monto_aplicar = min(monto, factura.monto_pendiente)
    cobro = models.PagoFactura(
        factura_id=factura_id,
        monto=monto_aplicar,
        fecha_cobro=datetime.strptime(fecha_cobro, "%Y-%m-%d"),
        metodo_pago=metodo_pago,
        comprobante=comprobante.strip(),
        notas=notas.strip(),
    )
    db.add(cobro)
    factura.monto_cobrado = round(factura.monto_cobrado + monto_aplicar, 2)
    _actualizar_estado(factura)
    db.commit()
    return RedirectResponse(f"/facturas/{factura_id}/detalle?msg=Cobro+registrado+correctamente", status_code=303)


# ── Eliminar cobro ───────────────────────────────────────────────────────────

@router.post("/{factura_id}/cobros/{cobro_id}/eliminar")
def eliminar_cobro(factura_id: int, cobro_id: int, db: Session = Depends(get_db)):
    cobro = db.query(models.PagoFactura).filter(
        models.PagoFactura.id == cobro_id,
        models.PagoFactura.factura_id == factura_id,
    ).first()
    if not cobro:
        return RedirectResponse(f"/facturas/{factura_id}/detalle?error=Cobro+no+encontrado", status_code=303)
    factura = cobro.factura
    factura.monto_cobrado = max(0.0, round(factura.monto_cobrado - cobro.monto, 2))
    db.delete(cobro)
    _actualizar_estado(factura)
    db.commit()
    return RedirectResponse(f"/facturas/{factura_id}/detalle?msg=Cobro+eliminado+correctamente", status_code=303)


# ── Reporte HTML ─────────────────────────────────────────────────────────────

@router.get("/reporte")
def reporte_facturas(
    request: Request,
    db: Session = Depends(get_db),
    estado: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Factura)
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
    db: Session = Depends(get_db),
    estado: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Factura)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Factura.fecha_emision >= fd, models.Factura.fecha_emision <= fh)
    except ValueError:
        pass
    if estado:
        query = query.filter(models.Factura.estado == estado)

    facturas = query.order_by(models.Factura.fecha_vencimiento.asc().nullsfirst()).all()

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

    elements.append(Paragraph("TechStock — Reporte de Facturas / Cuentas por Cobrar", title_style))
    elements.append(Paragraph(
        f"Período: {fecha_desde} al {fecha_hasta}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))
    elements.append(Spacer(1, 0.3*cm))

    header = ["N° Factura", "Cliente", "Documento", "Concepto", "Emisión", "Vencimiento",
              "Total", "Cobrado", "Pendiente", "Estado"]
    data = [header]

    for f in facturas:
        estado_txt = "VENCIDA" if f.esta_vencida else f.estado
        data.append([
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

    data.append(["", "", "", "TOTAL", "", "",
                  f"${sum(f.monto_total for f in facturas):,.2f}",
                  f"${sum(f.monto_cobrado for f in facturas):,.2f}",
                  f"${sum(f.monto_pendiente for f in facturas):,.2f}", ""])

    col_widths = [2.4*cm, 4.5*cm, 2.5*cm, 4.5*cm, 2.2*cm, 2.2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.2*cm]
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
        ('ALIGN',      (1, 1), (3, -1), 'LEFT'),
        ('FONTSIZE',   (0, 1), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID',       (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
    ])

    for i, f in enumerate(facturas, start=1):
        estado_txt = "VENCIDA" if f.esta_vencida else f.estado
        color = ESTADO_COLORS.get(estado_txt)
        if color:
            style.add('BACKGROUND', (9, i), (9, i), color)

    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    filename = f"reporte_facturas_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={filename}"})


# ── Eliminar factura ─────────────────────────────────────────────────────────

@router.post("/{factura_id}/eliminar")
def eliminar_factura(factura_id: int, db: Session = Depends(get_db)):
    factura = db.query(models.Factura).filter(models.Factura.id == factura_id).first()
    if not factura:
        return RedirectResponse("/facturas?error=Factura+no+encontrada", status_code=303)
    db.delete(factura)
    db.commit()
    return RedirectResponse("/facturas?msg=Factura+eliminada+correctamente", status_code=303)
