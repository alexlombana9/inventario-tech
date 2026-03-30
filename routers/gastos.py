from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta

from database import get_db
from templates_config import templates
from auth import require_auth, log_audit, get_local_id
import models

router = APIRouter(prefix="/gastos", tags=["gastos"])

from utils.constants import TIPOS_GASTO, CATEGORIAS_GASTO, METODOS_PAGO


# ── Lista ─────────────────────────────────────────────────────

@router.get("")
def lista_gastos(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    tipo: str = None,
    categoria_gasto: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
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

    query = db.query(models.Gasto).filter(models.Gasto.activo == True)
    if local_id is not None:
        query = query.filter(models.Gasto.local_id == local_id)

    fd = fh = None
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Gasto.fecha >= fd, models.Gasto.fecha <= fh)
    except ValueError:
        fd = fh = None

    if tipo and tipo.strip():
        query = query.filter(models.Gasto.tipo == tipo)
    if categoria_gasto and categoria_gasto.strip():
        query = query.filter(models.Gasto.categoria_gasto == categoria_gasto)
    if buscar:
        query = query.filter(
            models.Gasto.concepto.ilike(f"%{buscar}%") |
            models.Gasto.comprobante.ilike(f"%{buscar}%")
        )

    from utils.pagination import paginate
    query = query.order_by(models.Gasto.fecha.desc())
    gastos, total, total_paginas = paginate(query, pag)

    sum_query = db.query(func.sum(models.Gasto.monto)).filter(
        models.Gasto.activo == True,
        models.Gasto.fecha >= fd if fd else True,
        models.Gasto.fecha <= fh if fh else True,
    )
    if local_id is not None:
        sum_query = sum_query.filter(models.Gasto.local_id == local_id)
    total_gastos = sum_query.scalar() or 0

    dir_query = db.query(func.sum(models.Gasto.monto)).filter(
        models.Gasto.activo == True,
        models.Gasto.tipo == "DIRECTO",
        models.Gasto.fecha >= fd if fd else True,
        models.Gasto.fecha <= fh if fh else True,
    )
    if local_id is not None:
        dir_query = dir_query.filter(models.Gasto.local_id == local_id)
    total_directos = dir_query.scalar() or 0

    indir_query = db.query(func.sum(models.Gasto.monto)).filter(
        models.Gasto.activo == True,
        models.Gasto.tipo == "INDIRECTO",
        models.Gasto.fecha >= fd if fd else True,
        models.Gasto.fecha <= fh if fh else True,
    )
    if local_id is not None:
        indir_query = indir_query.filter(models.Gasto.local_id == local_id)
    total_indirectos = indir_query.scalar() or 0

    return templates.TemplateResponse("gastos/lista.html", {
        "request": request,
        "gastos": gastos,
        "tipos_gasto": TIPOS_GASTO,
        "categorias_gasto": CATEGORIAS_GASTO,
        "tipo": tipo or "",
        "categoria_gasto": categoria_gasto or "",
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "buscar": buscar or "",
        "total": total,
        "total_gastos": total_gastos,
        "total_directos": total_directos,
        "total_indirectos": total_indirectos,
        "pagina": pag,
        "total_paginas": total_paginas,
        "msg": msg,
        "error": error,
    })


# ── Exportar Excel ─────────────────────────────────────────────

@router.get("/exportar")
def exportar_gastos(
    request: Request,
    db: Session = Depends(get_db),
    tipo: str = None,
    categoria_gasto: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    buscar: str = None,
):
    from utils.excel import generate_excel

    local_id = get_local_id(request)

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.Gasto).filter(models.Gasto.activo == True)
    if local_id is not None:
        query = query.filter(models.Gasto.local_id == local_id)

    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.Gasto.fecha >= fd, models.Gasto.fecha <= fh)
    except ValueError:
        pass

    if tipo and tipo.strip():
        query = query.filter(models.Gasto.tipo == tipo)
    if categoria_gasto and categoria_gasto.strip():
        query = query.filter(models.Gasto.categoria_gasto == categoria_gasto)
    if buscar:
        query = query.filter(
            models.Gasto.concepto.ilike(f"%{buscar}%") |
            models.Gasto.comprobante.ilike(f"%{buscar}%")
        )

    gastos = query.order_by(models.Gasto.fecha.desc()).all()

    headers = ["Fecha", "Concepto", "Tipo", "Categoria", "Monto",
               "Metodo Pago", "Comprobante", "Notas"]
    rows = []
    for g in gastos:
        rows.append([
            g.fecha.strftime("%d/%m/%Y") if g.fecha else "",
            g.concepto,
            g.tipo,
            g.categoria_gasto or "",
            g.monto,
            g.metodo_pago,
            g.comprobante or "",
            g.notas or "",
        ])

    output = generate_excel(
        "Listado de Gastos", headers, rows,
        col_widths=[14, 30, 14, 18, 14, 16, 16, 24],
        money_cols=[4],
    )
    filename = f"gastos_{fecha_desde}_{fecha_hasta}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Nuevo ─────────────────────────────────────────────────────

@router.get("/nuevo")
def nuevo_gasto_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    return templates.TemplateResponse("gastos/form.html", {
        "request": request,
        "gasto": None,
        "tipos_gasto": TIPOS_GASTO,
        "categorias_gasto": CATEGORIAS_GASTO,
        "metodos_pago": METODOS_PAGO,
    })


@router.post("/nuevo")
def crear_gasto(
    request: Request,
    concepto: str = Form(...),
    tipo: str = Form("DIRECTO"),
    categoria_gasto: str = Form(""),
    monto: str = Form(...),
    fecha: str = Form(""),
    metodo_pago: str = Form("EFECTIVO"),
    comprobante: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    try:
        monto_val = float(monto)
    except ValueError:
        return RedirectResponse("/gastos/nuevo?error=Monto+inválido", status_code=303)

    if monto_val <= 0:
        return RedirectResponse("/gastos/nuevo?error=El+monto+debe+ser+mayor+a+0", status_code=303)

    fecha_gasto = datetime.now()
    if fecha and fecha.strip():
        try:
            fecha_gasto = datetime.strptime(fecha.strip(), "%Y-%m-%d")
        except ValueError:
            pass

    local_id = get_local_id(request)
    gasto = models.Gasto(
        concepto=concepto.strip(),
        tipo=tipo,
        categoria_gasto=categoria_gasto.strip(),
        monto=monto_val,
        fecha=fecha_gasto,
        metodo_pago=metodo_pago,
        comprobante=comprobante.strip(),
        notas=notas.strip(),
    )
    gasto.local_id = local_id
    db.add(gasto)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "gasto", gasto.id,
              f"Gasto registrado: {concepto.strip()} por ${monto_val:,.2f} ({tipo})", ip)

    return RedirectResponse("/gastos?msg=Gasto+registrado+correctamente", status_code=303)


# ── Editar ────────────────────────────────────────────────────

@router.get("/{gasto_id}/editar")
def editar_gasto_form(
    gasto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Gasto).filter(
        models.Gasto.id == gasto_id, models.Gasto.activo == True
    )
    if local_id is not None:
        query = query.filter(models.Gasto.local_id == local_id)
    gasto = query.first()
    if not gasto:
        return RedirectResponse("/gastos?error=Gasto+no+encontrado", status_code=303)

    return templates.TemplateResponse("gastos/form.html", {
        "request": request,
        "gasto": gasto,
        "tipos_gasto": TIPOS_GASTO,
        "categorias_gasto": CATEGORIAS_GASTO,
        "metodos_pago": METODOS_PAGO,
    })


@router.post("/{gasto_id}/editar")
def actualizar_gasto(
    gasto_id: int,
    request: Request,
    concepto: str = Form(...),
    tipo: str = Form("DIRECTO"),
    categoria_gasto: str = Form(""),
    monto: str = Form(...),
    fecha: str = Form(""),
    metodo_pago: str = Form("EFECTIVO"),
    comprobante: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Gasto).filter(
        models.Gasto.id == gasto_id, models.Gasto.activo == True
    )
    if local_id is not None:
        query = query.filter(models.Gasto.local_id == local_id)
    gasto = query.first()
    if not gasto:
        return RedirectResponse("/gastos?error=Gasto+no+encontrado", status_code=303)

    try:
        monto_val = float(monto)
    except ValueError:
        return RedirectResponse(f"/gastos/{gasto_id}/editar?error=Monto+inválido", status_code=303)

    gasto.concepto = concepto.strip()
    gasto.tipo = tipo
    gasto.categoria_gasto = categoria_gasto.strip()
    gasto.monto = monto_val
    gasto.metodo_pago = metodo_pago
    gasto.comprobante = comprobante.strip()
    gasto.notas = notas.strip()

    if fecha and fecha.strip():
        try:
            gasto.fecha = datetime.strptime(fecha.strip(), "%Y-%m-%d")
        except ValueError:
            pass

    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "gasto", gasto.id,
              f"Gasto actualizado: {concepto.strip()} por ${monto_val:,.2f}", ip)

    return RedirectResponse("/gastos?msg=Gasto+actualizado", status_code=303)


# ── Eliminar (soft delete) ────────────────────────────────────

@router.post("/{gasto_id}/eliminar")
def eliminar_gasto(
    gasto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Gasto).filter(
        models.Gasto.id == gasto_id, models.Gasto.activo == True
    )
    if local_id is not None:
        query = query.filter(models.Gasto.local_id == local_id)
    gasto = query.first()
    if not gasto:
        return RedirectResponse("/gastos?error=Gasto+no+encontrado", status_code=303)

    gasto.activo = False
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "gasto", gasto.id,
              f"Gasto eliminado: {gasto.concepto}", ip)

    return RedirectResponse("/gastos?msg=Gasto+eliminado", status_code=303)
