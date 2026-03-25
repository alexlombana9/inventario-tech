"""
Autenticación y gestión de sesiones para TechStock.
Usa cookies firmadas con itsdangerous y hashing bcrypt.
"""
import os
import json
from datetime import datetime
from functools import wraps
from typing import List

from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from database import get_db
import models

# ── Password hashing ──────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Session cookie ────────────────────────────────────────
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), ".secret_key")
SESSION_MAX_AGE = 8 * 3600  # 8 horas
COOKIE_NAME = "techstock_session"


def _get_secret_key() -> str:
    """Lee o genera la clave secreta para firmar cookies."""
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "r") as f:
            return f.read().strip()
    key = os.urandom(32).hex()
    with open(SECRET_KEY_FILE, "w") as f:
        f.write(key)
    return key


_serializer = None


def get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(_get_secret_key())
    return _serializer


def create_session_cookie(user_id: int, username: str) -> str:
    """Genera el valor firmado de la cookie de sesión."""
    s = get_serializer()
    return s.dumps({"user_id": user_id, "username": username})


def decode_session_cookie(cookie_value: str) -> dict | None:
    """Decodifica la cookie. Retorna dict o None si expirada/inválida."""
    s = get_serializer()
    try:
        return s.loads(cookie_value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


# ── Flash messages (reemplazo de ?msg= en URL) ───────────
FLASH_COOKIE = "techstock_flash"


def set_flash(response: RedirectResponse, message: str, category: str = "success") -> RedirectResponse:
    """Agrega un flash message a la respuesta como cookie."""
    s = get_serializer()
    value = s.dumps({"message": message, "category": category})
    response.set_cookie(FLASH_COOKIE, value, httponly=True, samesite="lax", max_age=60)
    return response


def get_flash(request: Request) -> dict | None:
    """Lee y consume el flash message del request."""
    cookie = request.cookies.get(FLASH_COOKIE)
    if not cookie:
        return None
    s = get_serializer()
    try:
        return s.loads(cookie, max_age=60)
    except (BadSignature, SignatureExpired):
        return None


# ── Dependencies para rutas ───────────────────────────────

def get_current_user(request: Request) -> models.Usuario | None:
    """Obtiene el usuario actual desde request.state (inyectado por middleware)."""
    return getattr(request.state, "user", None)


def require_auth(request: Request) -> models.Usuario:
    """Dependencia que exige autenticación."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_role(*roles):
    """Factory de dependencia que exige un rol específico."""
    def dependency(request: Request) -> models.Usuario:
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=303, headers={"Location": "/login"})
        if user.rol not in roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para acceder a esta sección")
        return user
    return dependency


# ── Permission management ────────────────────────────────
MODULOS_DISPONIBLES = [
    ("dashboard", "Dashboard"),
    ("productos", "Productos"),
    ("categorias", "Categorias"),
    ("inventario", "Movimientos de Inventario"),
    ("ventas_pos", "Punto de Venta"),
    ("ventas_historial", "Historial de Ventas"),
    ("clientes", "Clientes"),
    ("caja", "Caja Registradora"),
    ("proveedores", "Proveedores"),
    ("acreedores", "Acreedores"),
    ("deudas", "Cuentas por Pagar"),
    ("facturas", "Cuentas por Cobrar"),
    ("reportes", "Reportes"),
]

PERMISOS_POR_ROL = {
    "ADMIN": [m[0] for m in MODULOS_DISPONIBLES],
    "VENDEDOR": [
        "dashboard", "productos", "ventas_pos", "ventas_historial",
        "clientes", "caja", "acreedores", "deudas", "facturas", "reportes",
    ],
    "BODEGUERO": [
        "dashboard", "productos", "categorias", "inventario",
        "proveedores", "reportes",
    ],
}


def get_user_permisos(user) -> list:
    """Obtiene la lista de permisos del usuario. Si tiene permisos personalizados los usa, si no los del rol."""
    if user.permisos and user.permisos.strip():
        return [p.strip() for p in user.permisos.split(",") if p.strip()]
    return PERMISOS_POR_ROL.get(user.rol, [])


def user_has_permiso(user, modulo: str) -> bool:
    """Verifica si el usuario tiene acceso a un modulo."""
    if user.rol == "ADMIN":
        return True
    return modulo in get_user_permisos(user)


def require_permiso(modulo: str):
    """Factory de dependencia que exige acceso a un modulo."""
    def dependency(request: Request) -> models.Usuario:
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=303, headers={"Location": "/login"})
        if not user_has_permiso(user, modulo):
            raise HTTPException(status_code=403, detail="No tienes permisos para acceder a esta seccion")
        return user
    return dependency


# ── Multi-account session management ─────────────────────
ACCOUNTS_COOKIE = "techstock_accounts"


def get_saved_accounts(request: Request) -> list:
    """Lee las cuentas guardadas de la cookie."""
    cookie = request.cookies.get(ACCOUNTS_COOKIE)
    if not cookie:
        return []
    s = get_serializer()
    try:
        return s.loads(cookie, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return []


def save_accounts_cookie(response, accounts: list):
    """Guarda la lista de cuentas en una cookie firmada."""
    s = get_serializer()
    value = s.dumps(accounts)
    response.set_cookie(
        ACCOUNTS_COOKIE, value,
        httponly=True, samesite="lax", max_age=SESSION_MAX_AGE,
    )
    return response


def remove_accounts_cookie(response):
    """Elimina la cookie de cuentas guardadas."""
    response.delete_cookie(ACCOUNTS_COOKIE)
    return response


# ── Audit trail ───────────────────────────────────────────

def log_audit(db: Session, user: models.Usuario | None, accion: str,
              entidad: str = "", entidad_id: int = None,
              detalle: str = "", ip: str = ""):
    """Registra una entrada en el log de auditoría."""
    entry = models.AuditLog(
        usuario_id=user.id if user else None,
        usuario_nombre=user.nombre_completo if user else "Sistema",
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()
