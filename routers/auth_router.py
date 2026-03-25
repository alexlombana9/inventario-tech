from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from templates_config import templates
from auth import (
    verify_password, create_session_cookie, decode_session_cookie,
    COOKIE_NAME, set_flash, log_audit,
    get_saved_accounts, save_accounts_cookie, remove_accounts_cookie,
)
import models

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(request: Request, error: str = None, agregar: str = None):
    user = getattr(request.state, "user", None)
    if user and not agregar:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": error,
        "agregar": agregar or "",
    })


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    agregar: str = Form(""),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(
        models.Usuario.username == username.strip().lower()
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Usuario o contrasena incorrectos",
            "agregar": agregar,
        })

    if not user.activo:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Tu cuenta esta desactivada. Contacta al administrador.",
            "agregar": agregar,
        })

    # Actualizar ultimo login
    user.ultimo_login = datetime.now()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "LOGIN", "usuario", user.id, f"Inicio de sesion: {user.username}", ip)

    # Crear cookie de sesion
    cookie_value = create_session_cookie(user.id, user.username)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME, cookie_value,
        httponly=True, samesite="lax", max_age=8 * 3600,
    )

    # Si estamos agregando una cuenta, guardar la sesion anterior en saved_accounts
    if agregar == "1":
        current_user = getattr(request.state, "user", None)
        accounts = get_saved_accounts(request)
        if current_user:
            # Guardar la cuenta actual en la lista de cuentas
            existing_ids = [a["user_id"] for a in accounts]
            if current_user.id not in existing_ids:
                current_cookie = request.cookies.get(COOKIE_NAME, "")
                accounts.append({
                    "user_id": current_user.id,
                    "username": current_user.username,
                    "nombre_completo": current_user.nombre_completo,
                    "foto": current_user.foto or "",
                    "rol": current_user.rol,
                    "cookie": current_cookie,
                })
        # Remover la nueva cuenta de saved si ya estaba
        accounts = [a for a in accounts if a["user_id"] != user.id]
        save_accounts_cookie(response, accounts)

    return set_flash(response, f"Bienvenido, {user.nombre_completo}")


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if user:
        ip = request.client.host if request.client else ""
        log_audit(db, user, "LOGOUT", "usuario", user.id, f"Cierre de sesion: {user.username}", ip)

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    remove_accounts_cookie(response)
    return response


@router.get("/cambiar-cuenta/{user_id}")
def cambiar_cuenta(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = getattr(request.state, "user", None)
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    accounts = get_saved_accounts(request)

    # Buscar la cuenta a la que se quiere cambiar
    target_account = None
    for acc in accounts:
        if acc["user_id"] == user_id:
            target_account = acc
            break

    if not target_account:
        response = RedirectResponse("/perfil", status_code=303)
        return set_flash(response, "Cuenta no encontrada en sesiones guardadas", "error")

    # Verificar que el usuario target siga activo
    target_user = db.query(models.Usuario).filter(
        models.Usuario.id == user_id,
        models.Usuario.activo == True,
    ).first()
    if not target_user:
        # Remover cuenta invalida de la lista
        accounts = [a for a in accounts if a["user_id"] != user_id]
        response = RedirectResponse("/perfil", status_code=303)
        save_accounts_cookie(response, accounts)
        return set_flash(response, "La cuenta ya no esta activa", "error")

    # Guardar la cuenta actual en saved_accounts
    existing_ids = [a["user_id"] for a in accounts]
    current_cookie = request.cookies.get(COOKIE_NAME, "")
    if current_user.id not in existing_ids:
        accounts.append({
            "user_id": current_user.id,
            "username": current_user.username,
            "nombre_completo": current_user.nombre_completo,
            "foto": current_user.foto or "",
            "rol": current_user.rol,
            "cookie": current_cookie,
        })

    # Remover la cuenta target de saved
    target_cookie = target_account.get("cookie", "")
    accounts = [a for a in accounts if a["user_id"] != user_id]

    # Crear nueva sesion para el usuario target
    ip = request.client.host if request.client else ""
    target_user.ultimo_login = datetime.now()
    db.commit()
    log_audit(db, target_user, "LOGIN", "usuario", target_user.id,
              f"Cambio de cuenta desde {current_user.username}", ip)

    new_cookie = create_session_cookie(target_user.id, target_user.username)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME, new_cookie,
        httponly=True, samesite="lax", max_age=8 * 3600,
    )
    save_accounts_cookie(response, accounts)
    return set_flash(response, f"Cambiaste a la cuenta de {target_user.nombre_completo}")


@router.get("/cerrar-cuenta/{user_id}")
def cerrar_cuenta_guardada(
    user_id: int,
    request: Request,
):
    """Remueve una cuenta guardada de la lista."""
    current_user = getattr(request.state, "user", None)
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    accounts = get_saved_accounts(request)
    accounts = [a for a in accounts if a["user_id"] != user_id]

    response = RedirectResponse("/perfil", status_code=303)
    save_accounts_cookie(response, accounts)
    return set_flash(response, "Sesion guardada removida")
