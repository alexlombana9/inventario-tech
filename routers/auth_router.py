from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from datetime import datetime

from database import get_db
from templates_config import templates
from auth import (
    verify_password, create_session_cookie, decode_session_cookie,
    hash_password, validate_password, cookie_kwargs,
    COOKIE_NAME, set_flash, log_audit, login_limiter, SESSION_MAX_AGE,
    get_saved_accounts, save_accounts_cookie, remove_accounts_cookie,
)
import models

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(request: Request, error: str = None, agregar: str = None, db: Session = Depends(get_db)):
    # Si no hay usuarios, redirigir al wizard de configuracion inicial
    try:
        count = db.query(models.Usuario).count()
        if count == 0:
            return RedirectResponse("/setup", status_code=303)
    except Exception:
        pass
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
    ip = request.client.host if request.client else "unknown"

    # Rate limiting: máximo 5 intentos por minuto por IP
    if login_limiter.is_limited(ip):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Demasiados intentos. Espera un momento antes de volver a intentar.",
            "agregar": agregar,
        })

    try:
        user = db.query(models.Usuario).filter(
            models.Usuario.username == username.strip().lower()
        ).first()
    except OperationalError:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Error de conexion a la base de datos. Verifica que PostgreSQL este activo.",
            "agregar": agregar,
        })

    if not user or not verify_password(password, user.password_hash):
        login_limiter.record(ip)
        log_audit(db, None, "LOGIN_FAILED", "usuario", None,
                  f"Intento fallido para usuario: {username.strip().lower()}", ip)
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
        **cookie_kwargs(), max_age=SESSION_MAX_AGE,
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
        **cookie_kwargs(), max_age=SESSION_MAX_AGE,
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


@router.get("/setup")
def setup_page(request: Request, error: str = None, db: Session = Depends(get_db)):
    """Wizard de configuracion inicial. Solo accesible cuando no hay usuarios."""
    count = db.query(models.Usuario).count()
    if count > 0:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("auth/setup.html", {
        "request": request,
        "error": error,
    })


@router.post("/setup")
def setup(
    request: Request,
    nombre_negocio: str = Form(...),
    nombre_completo: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirmar_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Crea la cuenta de administrador inicial y configura el negocio."""
    # Si ya existen usuarios, no permitir configuracion
    count = db.query(models.Usuario).count()
    if count > 0:
        return RedirectResponse("/login", status_code=303)

    # Validar contrasenas coincidan
    if password != confirmar_password:
        return templates.TemplateResponse("auth/setup.html", {
            "request": request,
            "error": "Las contrasenas no coinciden",
        })

    # Validar fortaleza de contrasena
    pwd_error = validate_password(password)
    if pwd_error:
        return templates.TemplateResponse("auth/setup.html", {
            "request": request,
            "error": pwd_error,
        })

    # Validar longitud de usuario
    if len(username.strip()) < 3:
        return templates.TemplateResponse("auth/setup.html", {
            "request": request,
            "error": "El usuario debe tener al menos 3 caracteres",
        })

    # Crear local si no existe
    local = db.query(models.Local).first()
    if not local:
        local = models.Local(nombre="Sede Principal", codigo="SEDE-001", activo=True)
        db.add(local)
        db.commit()

    # Crear usuario SUPERADMIN
    admin = models.Usuario(
        username=username.strip().lower(),
        password_hash=hash_password(password),
        nombre_completo=nombre_completo.strip(),
        rol="SUPERADMIN",
        local_id=None,
        activo=True,
    )
    db.add(admin)
    db.commit()

    # Configurar nombre del negocio
    config = db.query(models.Configuracion).first()
    if config:
        config.nombre_negocio = nombre_negocio.strip()
    else:
        config = models.Configuracion(
            nombre_negocio=nombre_negocio.strip(),
            moneda_simbolo="$",
            moneda_codigo="COP",
            mensaje_recibo="Gracias por su compra",
            local_id=local.id,
        )
        db.add(config)
    db.commit()

    return RedirectResponse("/login", status_code=303)
