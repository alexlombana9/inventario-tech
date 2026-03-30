"""CRUD de locales — Solo SUPERADMIN."""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from templates_config import templates
from auth import require_superadmin, log_audit, set_flash, encode_selected_local, cookie_kwargs, SELECTED_LOCAL_COOKIE
import models

router = APIRouter(prefix="/locales", tags=["locales"])


@router.get("")
def lista_locales(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
    q: str = "",
):
    query = db.query(models.Local)
    if q:
        query = query.filter(models.Local.nombre.ilike(f"%{q}%"))
    locales = query.order_by(models.Local.created_at.desc()).all()

    # Contar usuarios y ventas por local
    stats = {}
    for local in locales:
        n_usuarios = db.query(models.Usuario).filter(
            models.Usuario.local_id == local.id, models.Usuario.activo == True
        ).count()
        n_ventas = db.query(models.Venta).filter(
            models.Venta.local_id == local.id, models.Venta.estado == "COMPLETADA"
        ).count()
        stats[local.id] = {"usuarios": n_usuarios, "ventas": n_ventas}

    return templates.TemplateResponse("locales/lista.html", {
        "request": request,
        "current_user": current_user,
        "locales": locales,
        "stats": stats,
        "q": q,
    })


@router.get("/nuevo")
def form_nuevo_local(
    request: Request,
    current_user: models.Usuario = Depends(require_superadmin),
):
    return templates.TemplateResponse("locales/form.html", {
        "request": request,
        "current_user": current_user,
        "local": None,
    })


@router.post("/nuevo")
def crear_local(
    request: Request,
    nombre: str = Form(...),
    codigo: str = Form(...),
    direccion: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    ciudad: str = Form(""),
    responsable: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    # Validar código único
    existe = db.query(models.Local).filter(models.Local.codigo == codigo.strip().upper()).first()
    if existe:
        resp = RedirectResponse(f"/locales/nuevo?error=Ya+existe+un+local+con+código+{codigo}", status_code=303)
        return resp

    local = models.Local(
        nombre=nombre.strip(),
        codigo=codigo.strip().upper(),
        direccion=direccion.strip(),
        telefono=telefono.strip(),
        email=email.strip(),
        ciudad=ciudad.strip(),
        responsable=responsable.strip(),
    )
    db.add(local)
    db.commit()

    # Crear configuración por defecto para el nuevo local
    config = models.Configuracion(
        nombre_negocio=nombre.strip(),
        moneda_simbolo="$",
        moneda_codigo="COP",
        mensaje_recibo="Gracias por su compra",
        local_id=local.id,
    )
    db.add(config)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "local", local.id, f"Local '{local.nombre}' creado", ip)

    resp = RedirectResponse("/locales", status_code=303)
    set_flash(resp, f"Local '{local.nombre}' creado exitosamente", "success")
    return resp


@router.get("/{local_id}/editar")
def form_editar_local(
    request: Request,
    local_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    local = db.query(models.Local).filter(models.Local.id == local_id).first()
    if not local:
        return RedirectResponse("/locales?error=Local+no+encontrado", status_code=303)
    return templates.TemplateResponse("locales/form.html", {
        "request": request,
        "current_user": current_user,
        "local": local,
    })


@router.post("/{local_id}/editar")
def editar_local(
    request: Request,
    local_id: int,
    nombre: str = Form(...),
    codigo: str = Form(...),
    direccion: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    ciudad: str = Form(""),
    responsable: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    local = db.query(models.Local).filter(models.Local.id == local_id).first()
    if not local:
        return RedirectResponse("/locales?error=Local+no+encontrado", status_code=303)

    # Validar código único (excluyendo el actual)
    existe = db.query(models.Local).filter(
        models.Local.codigo == codigo.strip().upper(),
        models.Local.id != local_id,
    ).first()
    if existe:
        resp = RedirectResponse(f"/locales/{local_id}/editar?error=Código+ya+en+uso", status_code=303)
        return resp

    local.nombre = nombre.strip()
    local.codigo = codigo.strip().upper()
    local.direccion = direccion.strip()
    local.telefono = telefono.strip()
    local.email = email.strip()
    local.ciudad = ciudad.strip()
    local.responsable = responsable.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "local", local.id, f"Local '{local.nombre}' actualizado", ip)

    resp = RedirectResponse("/locales", status_code=303)
    set_flash(resp, f"Local '{local.nombre}' actualizado", "success")
    return resp


@router.post("/{local_id}/toggle")
def toggle_local(
    request: Request,
    local_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    local = db.query(models.Local).filter(models.Local.id == local_id).first()
    if not local:
        return RedirectResponse("/locales?error=Local+no+encontrado", status_code=303)

    local.activo = not local.activo
    db.commit()

    estado = "activado" if local.activo else "desactivado"
    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "local", local.id, f"Local '{local.nombre}' {estado}", ip)

    resp = RedirectResponse("/locales", status_code=303)
    set_flash(resp, f"Local '{local.nombre}' {estado}", "success")
    return resp


@router.get("/seleccionar/{local_id}")
def seleccionar_local(
    request: Request,
    local_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    """SUPERADMIN selecciona un local para trabajar en él."""
    local = db.query(models.Local).filter(models.Local.id == local_id, models.Local.activo == True).first()
    if not local:
        return RedirectResponse("/locales?error=Local+no+encontrado", status_code=303)

    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(SELECTED_LOCAL_COOKIE, encode_selected_local(local.id), **cookie_kwargs(), max_age=8 * 3600)
    set_flash(resp, f"Trabajando en: {local.nombre}", "info")
    return resp


@router.get("/deseleccionar")
def deseleccionar_local(
    request: Request,
    current_user: models.Usuario = Depends(require_superadmin),
):
    """SUPERADMIN vuelve al super dashboard."""
    resp = RedirectResponse("/super", status_code=303)
    resp.delete_cookie(SELECTED_LOCAL_COOKIE)
    return resp
