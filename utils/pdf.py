"""Generador de reportes PDF reutilizable con ReportLab."""
import io
from datetime import datetime, date


def generate_report_pdf(
    title: str,
    fecha_desde: str,
    fecha_hasta: str,
    headers: list[str],
    rows: list[list],
    totals_row: list,
    col_widths_cm: list[float],
    estado_col_index: int,
    estado_colors_map: dict | None = None,
):
    """Genera un PDF tabular con encabezado, datos y fila de totales.

    Args:
        title: Titulo del reporte (ej. "TechStock — Reporte de Deudas")
        fecha_desde/fecha_hasta: Periodo del reporte
        headers: Lista de encabezados de columna
        rows: Lista de filas (cada fila es una lista con estado_txt como ultimo dato util)
        totals_row: Fila de totales
        col_widths_cm: Anchos de columna en cm
        estado_col_index: Indice de la columna de estado (para colorear)
        estado_colors_map: Dict de estado -> HexColor string (ej. {"PENDIENTE": "#fff3cd"})
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    if estado_colors_map is None:
        estado_colors_map = {
            "PENDIENTE": "#fff3cd",
            "PARCIAL": "#cfe2ff",
            "PAGADO": "#d1e7dd",
            "VENCIDA": "#f8d7da",
        }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=15, alignment=TA_CENTER, spaceAfter=0.2 * cm,
    )
    sub_style = ParagraphStyle(
        "ReportSub", parent=styles["Normal"],
        fontSize=8, alignment=TA_CENTER, spaceAfter=0.4 * cm,
        textColor=colors.grey,
    )

    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(
        f"Período: {fecha_desde} al {fecha_hasta}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style,
    ))
    elements.append(Spacer(1, 0.3 * cm))

    data = [headers] + rows + [totals_row]
    col_widths = [w * cm for w in col_widths_cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    hex_colors = {
        k: colors.HexColor(v) for k, v in estado_colors_map.items()
    }

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4f8")),
    ])

    # Colorear celdas de estado por fila
    for i, row in enumerate(rows, start=1):
        estado_txt = row[estado_col_index] if estado_col_index < len(row) else ""
        color = hex_colors.get(estado_txt)
        if color:
            style.add("BACKGROUND", (estado_col_index, i), (estado_col_index, i), color)

    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
