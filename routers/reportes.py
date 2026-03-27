from fastapi import APIRouter, Request, Depends
from templates_config import templates
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from database import get_db
from auth import get_local_id
import models
import io

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("")
def reportes_index(request: Request):
    return RedirectResponse("/reportes/stock", status_code=303)


@router.get("/stock")
def reporte_stock(
    request: Request,
    db: Session = Depends(get_db),
    categoria_id: str = None,
    solo_bajo: str = None
):
    local_id = get_local_id(request)
    cat_id = int(categoria_id) if categoria_id and categoria_id.strip() else None
    es_solo_bajo = solo_bajo in ("true", "True", "1", "on") if solo_bajo else False

    query = db.query(models.Producto).filter(models.Producto.activo == True)
    if local_id is not None:
        query = query.filter(models.Producto.local_id == local_id)

    if cat_id:
        query = query.filter(models.Producto.categoria_id == cat_id)
    if es_solo_bajo:
        query = query.filter(models.Producto.stock_actual <= models.Producto.stock_minimo)

    productos = query.order_by(models.Producto.nombre).all()
    categorias = db.query(models.Categoria).order_by(models.Categoria.nombre).all()

    valor_total = sum(p.stock_actual * p.precio_costo for p in productos)
    valor_venta = sum(p.stock_actual * p.precio_venta for p in productos)
    total_bajo = sum(1 for p in productos if p.stock_bajo)

    return templates.TemplateResponse("reportes/stock.html", {
        "request": request,
        "productos": productos,
        "categorias": categorias,
        "categoria_id": cat_id,
        "solo_bajo": es_solo_bajo,
        "valor_total": valor_total,
        "valor_venta": valor_venta,
        "total_bajo": total_bajo,
        "fecha_reporte": datetime.now(),
    })


@router.get("/movimientos")
def reporte_movimientos(
    request: Request,
    db: Session = Depends(get_db),
    fecha_desde: str = None,
    fecha_hasta: str = None,
    tipo: str = None,
    categoria_id: str = None
):
    local_id = get_local_id(request)
    # Defaults: último mes
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.MovimientoInventario)
    if local_id is not None:
        query = query.filter(models.MovimientoInventario.local_id == local_id)

    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(
            models.MovimientoInventario.fecha >= fd,
            models.MovimientoInventario.fecha <= fh
        )
    except ValueError:
        pass

    if tipo and tipo in ("ENTRADA", "SALIDA", "AJUSTE"):
        query = query.filter(models.MovimientoInventario.tipo == tipo)

    movimientos = query.order_by(models.MovimientoInventario.fecha.desc()).all()

    cat_id = int(categoria_id) if categoria_id and categoria_id.strip() else None
    if cat_id:
        movimientos = [m for m in movimientos if m.producto and m.producto.categoria_id == cat_id]

    total_entradas = sum(m.cantidad for m in movimientos if m.tipo == "ENTRADA")
    total_salidas = sum(m.cantidad for m in movimientos if m.tipo == "SALIDA")
    valor_entradas = sum(m.cantidad * m.precio_unitario for m in movimientos if m.tipo == "ENTRADA")
    valor_salidas = sum(m.cantidad * m.precio_unitario for m in movimientos if m.tipo == "SALIDA")

    categorias = db.query(models.Categoria).order_by(models.Categoria.nombre).all()

    return templates.TemplateResponse("reportes/movimientos.html", {
        "request": request,
        "movimientos": movimientos,
        "categorias": categorias,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "tipo": tipo or "",
        "categoria_id": cat_id,
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "valor_entradas": valor_entradas,
        "valor_salidas": valor_salidas,
        "fecha_reporte": datetime.now(),
    })


@router.get("/stock/excel")
def reporte_stock_excel(
    request: Request,
    db: Session = Depends(get_db),
    categoria_id: str = None,
    solo_bajo: str = None
):
    from utils.excel import generate_excel

    local_id = get_local_id(request)
    cat_id = int(categoria_id) if categoria_id and categoria_id.strip() else None
    es_solo_bajo = solo_bajo in ("true", "True", "1", "on") if solo_bajo else False

    query = db.query(models.Producto).filter(models.Producto.activo == True)
    if local_id is not None:
        query = query.filter(models.Producto.local_id == local_id)
    if cat_id:
        query = query.filter(models.Producto.categoria_id == cat_id)
    if es_solo_bajo:
        query = query.filter(models.Producto.stock_actual <= models.Producto.stock_minimo)
    productos = query.order_by(models.Producto.nombre).all()

    headers = ["Código", "Producto", "Categoría", "Stock", "Mín.", "U.M.", "P. Costo", "P. Venta", "Valor Total", "Estado"]
    rows = []
    for p in productos:
        rows.append([
            p.codigo, p.nombre,
            p.categoria.nombre if p.categoria else "-",
            p.stock_actual, p.stock_minimo, p.unidad_medida,
            p.precio_costo, p.precio_venta,
            round(p.stock_actual * p.precio_costo, 2),
            "BAJO" if p.stock_bajo else "OK",
        ])

    output = generate_excel(
        "Reporte de Stock", headers, rows,
        col_widths=[14, 30, 16, 10, 10, 10, 14, 14, 16, 10],
        money_cols=[6, 7, 8],
    )
    filename = f"stock_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/movimientos/excel")
def reporte_movimientos_excel(
    request: Request,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    tipo: str = None,
    db: Session = Depends(get_db),
):
    from utils.excel import generate_excel

    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.MovimientoInventario)
    if local_id is not None:
        query = query.filter(models.MovimientoInventario.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.MovimientoInventario.fecha >= fd, models.MovimientoInventario.fecha <= fh)
    except ValueError:
        pass

    if tipo and tipo in ("ENTRADA", "SALIDA", "AJUSTE"):
        query = query.filter(models.MovimientoInventario.tipo == tipo)

    movimientos = query.order_by(models.MovimientoInventario.fecha.desc()).all()

    headers = ["Fecha", "Producto", "Tipo", "Cantidad", "Stock Ant.", "Stock Res.", "Precio Unit.", "Referencia", "Observaciones"]
    rows = []
    for m in movimientos:
        rows.append([
            m.fecha.strftime("%d/%m/%Y %H:%M"),
            m.producto.nombre if m.producto else "-",
            m.tipo, m.cantidad, m.stock_anterior, m.stock_resultante,
            m.precio_unitario, m.numero_referencia or "-",
            m.observaciones or "-",
        ])

    output = generate_excel(
        "Reporte de Movimientos", headers, rows,
        col_widths=[18, 28, 12, 12, 14, 14, 14, 16, 24],
        money_cols=[6],
    )
    filename = f"movimientos_{fecha_desde}_{fecha_hasta}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/stock/pdf")
def reporte_stock_pdf(
    request: Request,
    db: Session = Depends(get_db),
    categoria_id: str = None,
    solo_bajo: str = None
):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    local_id = get_local_id(request)
    cat_id = int(categoria_id) if categoria_id and categoria_id.strip() else None
    es_solo_bajo = solo_bajo in ("true", "True", "1", "on") if solo_bajo else False

    query = db.query(models.Producto).filter(models.Producto.activo == True)
    if local_id is not None:
        query = query.filter(models.Producto.local_id == local_id)
    if cat_id:
        query = query.filter(models.Producto.categoria_id == cat_id)
    if es_solo_bajo:
        query = query.filter(models.Producto.stock_actual <= models.Producto.stock_minimo)
    productos = query.order_by(models.Producto.nombre).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                             rightMargin=1.5*cm, leftMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    elements = []

    # Título
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=16, alignment=TA_CENTER, spaceAfter=0.3*cm)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                fontSize=9, alignment=TA_CENTER, spaceAfter=0.5*cm,
                                textColor=colors.grey)

    elements.append(Paragraph("TechStock - Reporte de Stock", title_style))
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    elements.append(Spacer(1, 0.3*cm))

    # Tabla
    header = ["Código", "Producto", "Categoría", "Stock", "Mín.", "U.M.", "P. Costo", "P. Venta", "Valor Total", "Estado"]
    data = [header]

    for p in productos:
        estado = "BAJO" if p.stock_bajo else "OK"
        data.append([
            p.codigo,
            p.nombre[:35],
            p.categoria.nombre if p.categoria else "-",
            f"{p.stock_actual:,.1f}",
            f"{p.stock_minimo:,.1f}",
            p.unidad_medida,
            f"${p.precio_costo:,.2f}",
            f"${p.precio_venta:,.2f}",
            f"${p.stock_actual * p.precio_costo:,.2f}",
            estado,
        ])

    valor_total = sum(p.stock_actual * p.precio_costo for p in productos)
    data.append(["", "TOTAL", "", "", "", "", "", "", f"${valor_total:,.2f}", ""])

    col_widths = [2.5*cm, 6.5*cm, 3*cm, 2*cm, 2*cm, 1.5*cm, 2.5*cm, 2.5*cm, 3*cm, 1.8*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
    ])

    # Resaltar filas con stock bajo
    for i, p in enumerate(productos, start=1):
        if p.stock_bajo:
            style.add('TEXTCOLOR', (9, i), (9, i), colors.red)
            style.add('FONTNAME', (9, i), (9, i), 'Helvetica-Bold')

    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"stock_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/movimientos/pdf")
def reporte_movimientos_pdf(
    request: Request,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    tipo: str = None,
    db: Session = Depends(get_db)
):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.MovimientoInventario)
    if local_id is not None:
        query = query.filter(models.MovimientoInventario.local_id == local_id)
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.MovimientoInventario.fecha >= fd,
                              models.MovimientoInventario.fecha <= fh)
    except ValueError:
        pass

    if tipo and tipo in ("ENTRADA", "SALIDA", "AJUSTE"):
        query = query.filter(models.MovimientoInventario.tipo == tipo)

    movimientos = query.order_by(models.MovimientoInventario.fecha.desc()).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                             rightMargin=1.5*cm, leftMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=16, alignment=TA_CENTER, spaceAfter=0.3*cm)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                fontSize=9, alignment=TA_CENTER, spaceAfter=0.5*cm,
                                textColor=colors.grey)

    elements.append(Paragraph("TechStock - Reporte de Movimientos", title_style))
    elements.append(Paragraph(
        f"Período: {fecha_desde} al {fecha_hasta} | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))
    elements.append(Spacer(1, 0.3*cm))

    header = ["Fecha", "Producto", "Tipo", "Cantidad", "Stock Ant.", "Stock Res.", "Precio Unit.", "Referencia", "Observaciones"]
    data = [header]

    for m in movimientos:
        data.append([
            m.fecha.strftime("%d/%m/%Y %H:%M"),
            (m.producto.nombre[:30] if m.producto else "-"),
            m.tipo,
            f"{m.cantidad:,.2f}",
            f"{m.stock_anterior:,.2f}",
            f"{m.stock_resultante:,.2f}",
            f"${m.precio_unitario:,.2f}",
            m.numero_referencia or "-",
            (m.observaciones[:25] if m.observaciones else "-"),
        ])

    col_widths = [3.2*cm, 5.5*cm, 2*cm, 2*cm, 2.3*cm, 2.3*cm, 2.5*cm, 3*cm, 4.2*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    tipo_colores = {"ENTRADA": colors.HexColor('#d4edda'), "SALIDA": colors.HexColor('#f8d7da'), "AJUSTE": colors.HexColor('#fff3cd')}
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (8, 1), (8, -1), 'LEFT'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ])

    for i, m in enumerate(movimientos, start=1):
        color = tipo_colores.get(m.tipo)
        if color:
            style.add('BACKGROUND', (2, i), (2, i), color)

    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    filename = f"movimientos_{fecha_desde}_{fecha_hasta}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={filename}"})
