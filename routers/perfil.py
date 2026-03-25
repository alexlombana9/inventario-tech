from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from templates_config import templates
from auth import require_auth, hash_password, verify_password, set_flash, log_audit, COOKIE_NAME
import models

router = APIRouter(prefix="/perfil", tags=["perfil"])


@router.get("")
def perfil_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    return templates.TemplateResponse("perfil/index.html", {
        "request": request,
        "usuario": current_user,
    })


@router.post("")
def actualizar_perfil(
    request: Request,
    nombre_completo: str = Form(...),
    email: str = Form(""),
    telefono: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    nombre_clean = nombre_completo.strip()
    if not nombre_clean:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "El nombre completo es obligatorio", "error")

    current_user.nombre_completo = nombre_clean
    current_user.email = email.strip()
    current_user.telefono = telefono.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "perfil", current_user.id,
              "Perfil actualizado", ip)

    resp = RedirectResponse("/perfil", status_code=303)
    return set_flash(resp, "Perfil actualizado correctamente")


@router.post("/password")
def cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirmar: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    if not verify_password(password_actual, current_user.password_hash):
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "La contraseña actual es incorrecta", "error")

    if len(password_nueva) < 8:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "La nueva contraseña debe tener al menos 8 caracteres", "error")

    if password_nueva != password_confirmar:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "Las contraseñas nuevas no coinciden", "error")

    current_user.password_hash = hash_password(password_nueva)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "perfil", current_user.id,
              "Contraseña cambiada", ip)

    resp = RedirectResponse("/perfil", status_code=303)
    return set_flash(resp, "Contraseña cambiada correctamente")
