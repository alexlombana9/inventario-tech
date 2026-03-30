from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date

from database import get_db
from templates_config import templates
from auth import require_auth, log_audit, get_local_id
import models

router = APIRouter(prefix="/caja", tags=["caja"])


def _caja_abierta(db: Session, user_id: int, local_id: int | None = None) -> models.Caja | None:
    query = db.query(models.Caja).filter(
        models.Caja.usuario_id == user_id,
        models.Caja.estado == "ABIERTA"
    )
    if local_id is not None:
        query = query.filter(models.Caja.local_id == local_id)
    return query.first()


# ── Estado actual ────────────────────────────────────────────

@router.get("")
def estado_caja(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    msg: str = None,
    error: str = None,
):
    local_id = get_local_id(request)
    caja = _caja_abierta(db, current_user.id, local_id)

    return templates.TemplateResponse("caja/estado.html", {
        "request": request,
        "caja": caja,
        "msg": msg,
        "error": error,
    })


# ── Abrir caja ───────────────────────────────────────────────

@router.get("/abrir")
def abrir_caja_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    caja = _caja_abierta(db, current_user.id, local_id)
    if caja:
        return RedirectResponse("/caja?error=Ya+tienes+una+caja+abierta", status_code=303)

    return templates.TemplateResponse("caja/abrir.html", {
        "request": request,
    })


@router.post("/abrir")
def abrir_caja(
    request: Request,
    monto_apertura: float = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)

    try:
        # Lock del usuario para serializar apertura de caja y evitar duplicados
        db.query(models.Usuario).filter(
            models.Usuario.id == current_user.id
        ).with_for_update().first()

        existente = _caja_abierta(db, current_user.id, local_id)
        if existente:
            db.rollback()
            return RedirectResponse("/caja?error=Ya+tienes+una+caja+abierta", status_code=303)

        caja = models.Caja(
            usuario_id=current_user.id,
            monto_apertura=monto_apertura,
            fecha_apertura=datetime.now(),
        )
        caja.local_id = local_id
        db.add(caja)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/caja?error=Error+al+abrir+la+caja", status_code=303)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "caja", caja.id,
              f"Caja abierta con ${monto_apertura:,.2f}", ip)

    return RedirectResponse("/caja?msg=Caja+abierta+correctamente", status_code=303)


# ── Cerrar caja ──────────────────────────────────────────────

@router.get("/cerrar")
def cerrar_caja_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    caja = _caja_abierta(db, current_user.id, local_id)
    if not caja:
        return RedirectResponse("/caja?error=No+tienes+caja+abierta", status_code=303)

    return templates.TemplateResponse("caja/cerrar.html", {
        "request": request,
        "caja": caja,
    })


@router.post("/cerrar")
def cerrar_caja(
    request: Request,
    monto_cierre_real: float = Form(...),
    notas_cierre: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    caja = _caja_abierta(db, current_user.id, local_id)
    if not caja:
        return RedirectResponse("/caja?error=No+tienes+caja+abierta", status_code=303)

    esperado = caja.saldo_esperado
    caja.monto_cierre_esperado = round(esperado, 2)
    caja.monto_cierre_real = round(monto_cierre_real, 2)
    caja.diferencia = round(monto_cierre_real - esperado, 2)
    caja.estado = "CERRADA"
    caja.fecha_cierre = datetime.now()
    caja.notas_cierre = notas_cierre.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "caja", caja.id,
              f"Caja cerrada. Esperado: ${esperado:,.2f}, Real: ${monto_cierre_real:,.2f}, Dif: ${caja.diferencia:,.2f}", ip)

    return RedirectResponse(f"/caja/{caja.id}/detalle?msg=Caja+cerrada+correctamente", status_code=303)


# ── Movimiento manual ────────────────────────────────────────

@router.post("/movimiento")
def registrar_movimiento_caja(
    request: Request,
    tipo: str = Form(...),
    concepto: str = Form(...),
    monto: float = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    caja = _caja_abierta(db, current_user.id, local_id)
    if not caja:
        return RedirectResponse("/caja?error=No+tienes+caja+abierta", status_code=303)

    if monto <= 0:
        return RedirectResponse("/caja?error=El+monto+debe+ser+mayor+a+cero", status_code=303)

    mov = models.MovimientoCaja(
        caja_id=caja.id,
        tipo=tipo,
        concepto=concepto.strip(),
        monto=round(monto, 2),
        referencia_tipo="OTRO",
    )
    mov.local_id = local_id
    db.add(mov)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "movimiento_caja", mov.id,
              f"{tipo} manual en caja #{caja.id}: ${monto:,.2f} - {concepto.strip()}", ip)

    return RedirectResponse(f"/caja?msg=Movimiento+registrado+correctamente", status_code=303)


# ── Historial ────────────────────────────────────────────────

@router.get("/historial")
def historial_cajas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    buscar: str = None,
    estado: str = None,
    pagina: str = None,
):
    pag = int(pagina) if pagina and pagina.strip() else 1
    local_id = get_local_id(request)

    query = db.query(models.Caja).options(joinedload(models.Caja.usuario))
    if local_id is not None:
        query = query.filter(models.Caja.local_id == local_id)

    if current_user.rol != "ADMIN":
        query = query.filter(models.Caja.usuario_id == current_user.id)
    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.Caja.notas_cierre.ilike(term)
            | models.Caja.usuario.has(models.Usuario.nombre_completo.ilike(term))
        )
    if estado and estado in ("ABIERTA", "CERRADA"):
        query = query.filter(models.Caja.estado == estado)

    total = query.count()
    por_pagina = 20
    cajas = query.order_by(models.Caja.fecha_apertura.desc()).offset((pag - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    return templates.TemplateResponse("caja/historial.html", {
        "request": request,
        "cajas": cajas,
        "buscar": buscar or "",
        "estado": estado or "",
        "pagina": pag,
        "total_paginas": total_paginas,
        "total": total,
    })


# ── Detalle ──────────────────────────────────────────────────

@router.get("/{caja_id}/detalle")
def detalle_caja(
    caja_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    msg: str = None,
):
    local_id = get_local_id(request)
    query = db.query(models.Caja).options(
        joinedload(models.Caja.movimientos),
        joinedload(models.Caja.usuario),
    ).filter(models.Caja.id == caja_id)
    if local_id is not None:
        query = query.filter(models.Caja.local_id == local_id)
    caja = query.first()
    if not caja:
        return RedirectResponse("/caja/historial?error=Caja+no+encontrada", status_code=303)

    return templates.TemplateResponse("caja/detalle.html", {
        "request": request,
        "caja": caja,
        "msg": msg,
    })
