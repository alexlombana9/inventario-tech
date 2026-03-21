"""
Autenticación y gestión de sesiones para TechStock.
Usa cookies firmadas con itsdangerous y hashing bcrypt.
"""
import os
import json
from datetime import datetime
from functools import wraps

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
