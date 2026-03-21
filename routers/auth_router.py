from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from templates_config import templates
from auth import (
    verify_password, create_session_cookie, COOKIE_NAME,
    set_flash, log_audit
)
import models

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(request: Request, error: str = None):
    # Si ya tiene sesión, redirigir al dashboard
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": error,
    })


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(
        models.Usuario.username == username.strip().lower()
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Usuario o contraseña incorrectos",
        })

    if not user.activo:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Tu cuenta está desactivada. Contacta al administrador.",
        })

    # Actualizar último login
    user.ultimo_login = datetime.now()
    db.commit()

    # Registrar en auditoría
    ip = request.client.host if request.client else ""
    log_audit(db, user, "LOGIN", "usuario", user.id, f"Inicio de sesión: {user.username}", ip)

    # Crear cookie de sesión
    cookie_value = create_session_cookie(user.id, user.username)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        cookie_value,
        httponly=True,
        samesite="lax",
        max_age=8 * 3600,
    )
    return set_flash(response, f"Bienvenido, {user.nombre_completo}")


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if user:
        ip = request.client.host if request.client else ""
        log_audit(db, user, "LOGOUT", "usuario", user.id, f"Cierre de sesión: {user.username}", ip)

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
