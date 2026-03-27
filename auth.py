"""
Autenticación y gestión de sesiones para TechStock.
Usa cookies firmadas con itsdangerous y hashing bcrypt.
"""
import os
import re
import json
import time
import threading
from datetime import datetime
from functools import wraps
from typing import List
from collections import defaultdict

from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from database import get_db
import models

# ── Password hashing & validation ─────────────────────────

PASSWORD_MIN_LENGTH = 8


def validate_password(password: str) -> str | None:
    """Valida fortaleza de contraseña. Retorna mensaje de error o None si es válida."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres"
    if not re.search(r"[A-Z]", password):
        return "La contraseña debe tener al menos una letra mayúscula"
    if not re.search(r"[a-z]", password):
        return "La contraseña debe tener al menos una letra minúscula"
    if not re.search(r"\d", password):
        return "La contraseña debe tener al menos un número"
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Rate limiter in-memory (sin dependencias externas) ────

class RateLimiter:
    """Limita intentos por IP. Thread-safe."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_limited(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            attempts = self._attempts[key]
            # Limpiar intentos fuera de la ventana
            self._attempts[key] = [t for t in attempts if now - t < self.window]
            return len(self._attempts[key]) >= self.max_attempts

    def record(self, key: str):
        with self._lock:
            self._attempts[key].append(time.time())

    def remaining(self, key: str) -> int:
        now = time.time()
        with self._lock:
            valid = [t for t in self._attempts[key] if now - t < self.window]
            return max(0, self.max_attempts - len(valid))


login_limiter = RateLimiter(max_attempts=5, window_seconds=60)


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


_serializer = URLSafeTimedSerializer(_get_secret_key())


def get_serializer() -> URLSafeTimedSerializer:
    return _serializer


# ── CSRF Protection ──────────────────────────────────────
CSRF_MAX_AGE = 3600  # 1 hora


def generate_csrf_token(session_cookie: str) -> str:
    """Genera un token CSRF vinculado a la sesion del usuario."""
    s = get_serializer()
    return s.dumps({"csrf": True, "session": session_cookie[:16]})


def validate_csrf_token(token: str, session_cookie: str) -> bool:
    """Valida el token CSRF contra la sesion actual."""
    if not token or not session_cookie:
        return False
    s = get_serializer()
    try:
        data = s.loads(token, max_age=CSRF_MAX_AGE)
        return data.get("csrf") is True and data.get("session") == session_cookie[:16]
    except (BadSignature, SignatureExpired):
        return False


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
    """Factory de dependencia que exige un rol específico. SUPERADMIN pasa siempre."""
    def dependency(request: Request) -> models.Usuario:
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=303, headers={"Location": "/login"})
        if user.rol == "SUPERADMIN":
            return user
        if user.rol not in roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para acceder a esta sección")
        return user
    return dependency


def require_superadmin(request: Request) -> models.Usuario:
    """Dependencia que exige rol SUPERADMIN."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.rol != "SUPERADMIN":
        raise HTTPException(status_code=403, detail="Acceso restringido a Super Administrador")
    return user


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
    ("gastos", "Gastos"),
    ("reportes", "Reportes"),
]

# Módulos exclusivos del SUPERADMIN (no aparecen en permisos de local)
MODULOS_SUPER = [
    ("locales", "Gestión de Locales"),
    ("super_dashboard", "Dashboard General"),
    ("super_usuarios", "Usuarios Globales"),
]

PERMISOS_POR_ROL = {
    "SUPERADMIN": [m[0] for m in MODULOS_DISPONIBLES] + [m[0] for m in MODULOS_SUPER],
    "ADMIN": [m[0] for m in MODULOS_DISPONIBLES],
    "VENDEDOR": [
        "dashboard", "productos", "ventas_pos", "ventas_historial",
        "clientes", "caja", "acreedores", "deudas", "facturas", "gastos", "reportes",
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
    if user.rol in ("SUPERADMIN", "ADMIN"):
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

def get_local_id(request_or_user) -> int | None:
    """Obtiene el local_id efectivo del usuario o request.

    Para SUPERADMIN: usa selected_local_id de request.state (cookie) si disponible.
    Para otros roles: usa user.local_id.
    """
    if isinstance(request_or_user, models.Usuario):
        user = request_or_user
        if user.rol == "SUPERADMIN":
            return None
        return user.local_id

    # Es un Request
    user = getattr(request_or_user.state, "user", None)
    if not user:
        return None
    if user.rol == "SUPERADMIN":
        return getattr(request_or_user.state, "selected_local_id", None)
    return user.local_id


def log_audit(db: Session, user: models.Usuario | None, accion: str,
              entidad: str = "", entidad_id: int = None,
              detalle: str = "", ip: str = "", local_id: int = None):
    """Registra una entrada en el log de auditoría."""
    if local_id is None and user:
        local_id = user.local_id
    entry = models.AuditLog(
        usuario_id=user.id if user else None,
        usuario_nombre=user.nombre_completo if user else "Sistema",
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
        ip_address=ip,
        local_id=local_id,
    )
    db.add(entry)
    db.commit()
