import os
import io
from datetime import datetime
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from templates_config import templates
from auth import require_role, log_audit
import models

router = APIRouter(prefix="/importar", tags=["importar"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Página principal de importación ─────────────────────────────

@router.get("")
def importar_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    msg: str = None,
    error: str = None,
):
    return templates.TemplateResponse("importar/index.html", {
        "request": request,
        "msg": msg,
        "error": error,
    })


# ── Descargar plantillas Excel ──────────────────────────────────

@router.get("/plantilla/{tipo}")
def descargar_plantilla(
    tipo: str,
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    HEADER_FILL = PatternFill(start_color="1a1a2e", end_color="1a1a2e", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    THIN_BORDER = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    plantillas = {
        "productos": {
            "headers": ["codigo", "nombre", "descripcion", "categoria", "proveedor",
                        "precio_costo", "precio_venta", "stock_actual", "stock_minimo", "unidad_medida"],
            "widths": [15, 30, 35, 18, 20, 15, 15, 14, 14, 14],
            "ejemplo": ["PROD-001", "Teclado Mecánico", "Teclado gaming RGB", "Periféricos",
                        "TechDistribuidor", 45000, 89000, 25, 5, "UND"],
        },
        "clientes": {
            "headers": ["nombre", "tipo_documento", "documento", "telefono", "email", "direccion", "notas"],
            "widths": [25, 18, 18, 15, 25, 30, 30],
            "ejemplo": ["Juan Pérez", "CC", "1234567890", "3001234567",
                        "juan@email.com", "Calle 123 #45-67", "Cliente frecuente"],
        },
        "proveedores": {
            "headers": ["nombre", "contacto", "telefono", "email", "direccion", "nit_ruc"],
            "widths": [25, 20, 15, 25, 30, 18],
            "ejemplo": ["TechDistribuidor S.A.", "María López", "6011234567",
                        "ventas@techdist.com", "Av. Industrial 456", "900123456-1"],
        },
    }

    if tipo not in plantillas:
        return RedirectResponse("/importar?error=Tipo+de+plantilla+no+válido", status_code=303)

    config = plantillas[tipo]
    wb = Workbook()
    ws = wb.active
    ws.title = tipo.capitalize()

    # Encabezados
    for col_idx, header in enumerate(config["headers"], 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # Fila de ejemplo
    for col_idx, val in enumerate(config["ejemplo"], 1):
        cell = ws.cell(row=2, column=col_idx, value=val)
        cell.font = Font(name="Calibri", size=10, color="888888", italic=True)
        cell.border = THIN_BORDER

    # Anchos
    from openpyxl.utils import get_column_letter
    for i, w in enumerate(config["widths"], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"plantilla_{tipo}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Procesar importación ────────────────────────────────────────

@router.post("/procesar")
async def procesar_importacion(
    request: Request,
    tipo: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    # Validar tipo de archivo
    if not archivo.filename.endswith((".xlsx", ".xls")):
        return RedirectResponse("/importar?error=Solo+se+permiten+archivos+Excel+(.xlsx,+.xls)", status_code=303)

    # Leer archivo
    content = await archivo.read()
    if len(content) > MAX_FILE_SIZE:
        return RedirectResponse("/importar?error=El+archivo+excede+el+tamaño+máximo+(10MB)", status_code=303)

    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
    except Exception:
        return RedirectResponse("/importar?error=No+se+pudo+leer+el+archivo+Excel", status_code=303)

    # Leer encabezados
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return RedirectResponse("/importar?error=El+archivo+está+vacío+o+solo+tiene+encabezados", status_code=303)

    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    data_rows = rows[1:]

    # Despachar según tipo
    if tipo == "productos":
        result = _importar_productos(db, headers, data_rows, current_user, request)
    elif tipo == "clientes":
        result = _importar_clientes(db, headers, data_rows, current_user, request)
    elif tipo == "proveedores":
        result = _importar_proveedores(db, headers, data_rows, current_user, request)
    else:
        return RedirectResponse("/importar?error=Tipo+de+importación+no+válido", status_code=303)

    wb.close()
    return result


def _col_index(headers: list, name: str) -> int | None:
    """Busca el índice de una columna por nombre."""
    try:
        return headers.index(name)
    except ValueError:
        return None


def _cell_str(row, idx) -> str:
    if idx is None or idx >= len(row):
        return ""
    val = row[idx]
    return str(val).strip() if val is not None else ""


def _cell_float(row, idx, default=0.0) -> float:
    if idx is None or idx >= len(row):
        return default
    val = row[idx]
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ── Importar Productos ──────────────────────────────────────────

def _importar_productos(db: Session, headers: list, data_rows: list, user, request: Request):
    col_codigo = _col_index(headers, "codigo")
    col_nombre = _col_index(headers, "nombre")
    col_desc = _col_index(headers, "descripcion")
    col_cat = _col_index(headers, "categoria")
    col_prov = _col_index(headers, "proveedor")
    col_pcosto = _col_index(headers, "precio_costo")
    col_pventa = _col_index(headers, "precio_venta")
    col_stock = _col_index(headers, "stock_actual")
    col_smin = _col_index(headers, "stock_minimo")
    col_um = _col_index(headers, "unidad_medida")

    if col_codigo is None or col_nombre is None:
        return RedirectResponse(
            "/importar?error=El+archivo+debe+tener+las+columnas+'codigo'+y+'nombre'",
            status_code=303,
        )

    creados = 0
    actualizados = 0
    errores = []
    cat_cache = {}
    prov_cache = {}

    for i, row in enumerate(data_rows, start=2):
        codigo = _cell_str(row, col_codigo)
        nombre = _cell_str(row, col_nombre)

        if not codigo or not nombre:
            errores.append(f"Fila {i}: código o nombre vacío, omitida")
            continue

        # Buscar o crear categoría
        categoria_id = None
        cat_nombre = _cell_str(row, col_cat)
        if cat_nombre:
            if cat_nombre not in cat_cache:
                cat_obj = db.query(models.Categoria).filter(
                    models.Categoria.nombre.ilike(cat_nombre)
                ).first()
                if not cat_obj:
                    cat_obj = models.Categoria(nombre=cat_nombre)
                    db.add(cat_obj)
                    db.flush()
                cat_cache[cat_nombre] = cat_obj.id
            categoria_id = cat_cache[cat_nombre]

        # Buscar proveedor
        proveedor_id = None
        prov_nombre = _cell_str(row, col_prov)
        if prov_nombre:
            if prov_nombre not in prov_cache:
                prov_obj = db.query(models.Proveedor).filter(
                    models.Proveedor.nombre.ilike(prov_nombre)
                ).first()
                prov_cache[prov_nombre] = prov_obj.id if prov_obj else None
            proveedor_id = prov_cache[prov_nombre]

        # Buscar producto existente por código
        existente = db.query(models.Producto).filter(models.Producto.codigo == codigo).first()

        if existente:
            existente.nombre = nombre
            existente.descripcion = _cell_str(row, col_desc) or existente.descripcion
            if categoria_id:
                existente.categoria_id = categoria_id
            if proveedor_id:
                existente.proveedor_id = proveedor_id
            pc = _cell_float(row, col_pcosto)
            pv = _cell_float(row, col_pventa)
            if pc > 0:
                existente.precio_costo = pc
            if pv > 0:
                existente.precio_venta = pv
            stock_new = _cell_float(row, col_stock)
            if col_stock is not None and stock_new > 0:
                existente.stock_actual = stock_new
            smin = _cell_float(row, col_smin)
            if smin > 0:
                existente.stock_minimo = smin
            um = _cell_str(row, col_um)
            if um:
                existente.unidad_medida = um
            actualizados += 1
        else:
            stock_val = _cell_float(row, col_stock)
            producto = models.Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=_cell_str(row, col_desc),
                categoria_id=categoria_id,
                proveedor_id=proveedor_id,
                precio_costo=_cell_float(row, col_pcosto),
                precio_venta=_cell_float(row, col_pventa),
                stock_actual=stock_val,
                stock_minimo=_cell_float(row, col_smin),
                unidad_medida=_cell_str(row, col_um) or "UND",
            )
            db.add(producto)
            db.flush()

            # Registrar movimiento de entrada inicial si tiene stock
            if stock_val > 0:
                mov = models.MovimientoInventario(
                    producto_id=producto.id,
                    tipo="ENTRADA",
                    cantidad=stock_val,
                    stock_anterior=0,
                    stock_resultante=stock_val,
                    precio_unitario=_cell_float(row, col_pcosto),
                    observaciones="Importación desde Excel",
                )
                db.add(mov)

            creados += 1

    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "CREATE", "importacion", None,
              f"Importación productos: {creados} creados, {actualizados} actualizados", ip)

    msg_parts = []
    if creados:
        msg_parts.append(f"{creados} productos creados")
    if actualizados:
        msg_parts.append(f"{actualizados} actualizados")
    if errores:
        msg_parts.append(f"{len(errores)} errores")

    msg = "Importación completada: " + ", ".join(msg_parts) if msg_parts else "No se importaron datos"
    return RedirectResponse(f"/importar?msg={msg.replace(' ', '+')}", status_code=303)


# ── Importar Clientes ───────────────────────────────────────────

def _importar_clientes(db: Session, headers: list, data_rows: list, user, request: Request):
    col_nombre = _col_index(headers, "nombre")
    col_tipodoc = _col_index(headers, "tipo_documento")
    col_doc = _col_index(headers, "documento")
    col_tel = _col_index(headers, "telefono")
    col_email = _col_index(headers, "email")
    col_dir = _col_index(headers, "direccion")
    col_notas = _col_index(headers, "notas")

    if col_nombre is None:
        return RedirectResponse(
            "/importar?error=El+archivo+debe+tener+la+columna+'nombre'",
            status_code=303,
        )

    creados = 0
    omitidos = 0

    for i, row in enumerate(data_rows, start=2):
        nombre = _cell_str(row, col_nombre)
        if not nombre:
            omitidos += 1
            continue

        documento = _cell_str(row, col_doc)

        # Verificar duplicado por documento si existe
        if documento:
            existente = db.query(models.Cliente).filter(
                models.Cliente.documento == documento
            ).first()
            if existente:
                omitidos += 1
                continue

        cliente = models.Cliente(
            nombre=nombre,
            tipo_documento=_cell_str(row, col_tipodoc) or "CC",
            documento=documento,
            telefono=_cell_str(row, col_tel),
            email=_cell_str(row, col_email),
            direccion=_cell_str(row, col_dir),
            notas=_cell_str(row, col_notas),
        )
        db.add(cliente)
        creados += 1

    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "CREATE", "importacion", None,
              f"Importación clientes: {creados} creados, {omitidos} omitidos", ip)

    msg = f"Importación completada: {creados} clientes creados"
    if omitidos:
        msg += f", {omitidos} omitidos (duplicados o vacíos)"
    return RedirectResponse(f"/importar?msg={msg.replace(' ', '+')}", status_code=303)


# ── Importar Proveedores ────────────────────────────────────────

def _importar_proveedores(db: Session, headers: list, data_rows: list, user, request: Request):
    col_nombre = _col_index(headers, "nombre")
    col_contacto = _col_index(headers, "contacto")
    col_tel = _col_index(headers, "telefono")
    col_email = _col_index(headers, "email")
    col_dir = _col_index(headers, "direccion")
    col_nit = _col_index(headers, "nit_ruc")

    if col_nombre is None:
        return RedirectResponse(
            "/importar?error=El+archivo+debe+tener+la+columna+'nombre'",
            status_code=303,
        )

    creados = 0
    omitidos = 0

    for i, row in enumerate(data_rows, start=2):
        nombre = _cell_str(row, col_nombre)
        if not nombre:
            omitidos += 1
            continue

        # Verificar duplicado por nombre
        existente = db.query(models.Proveedor).filter(
            models.Proveedor.nombre.ilike(nombre)
        ).first()
        if existente:
            omitidos += 1
            continue

        proveedor = models.Proveedor(
            nombre=nombre,
            contacto=_cell_str(row, col_contacto),
            telefono=_cell_str(row, col_tel),
            email=_cell_str(row, col_email),
            direccion=_cell_str(row, col_dir),
            nit_ruc=_cell_str(row, col_nit),
        )
        db.add(proveedor)
        creados += 1

    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "CREATE", "importacion", None,
              f"Importación proveedores: {creados} creados, {omitidos} omitidos", ip)

    msg = f"Importación completada: {creados} proveedores creados"
    if omitidos:
        msg += f", {omitidos} omitidos (duplicados o vacíos)"
    return RedirectResponse(f"/importar?msg={msg.replace(' ', '+')}", status_code=303)
