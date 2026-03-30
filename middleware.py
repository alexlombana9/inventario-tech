"""
Middleware de autenticación, CSRF y cabeceras de seguridad para TechStock.
Valida la cookie de sesión en cada request y redirige a /login si no es válida.
Valida tokens CSRF en todas las peticiones POST.
Inyecta cabeceras de seguridad (OWASP) en todas las respuestas.
"""
import os
import re
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from database import SessionLocal
from auth import decode_session_cookie, validate_csrf_token, COOKIE_NAME, decode_selected_local, SELECTED_LOCAL_COOKIE
import models


# Rutas que NO requieren autenticación
PUBLIC_PATHS = {"/login", "/setup", "/favicon.ico", "/health", "/ready"}
PUBLIC_PREFIXES = ("/static/",)

# Rutas POST exentas de CSRF (APIs JSON internas)
CSRF_EXEMPT_PREFIXES = ("/ventas/api/", "/api/chatbot/")

# Deshabilitar CSRF en tests
_TESTING = os.environ.get("TESTING") == "1"

# Toggle de cabeceras de seguridad (usa config centralizada via env)
from config import settings
_SECURITY_HEADERS_ENABLED = settings.security_headers

# Cabeceras de seguridad OWASP
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    ),
}

# HSTS solo en produccion
_IS_PRODUCTION = os.environ.get("ENVIRONMENT") == "production"

# Regex para extraer csrf_token de multipart body
_MULTIPART_CSRF_RE = re.compile(rb'name="csrf_token"\r?\n\r?\n([^\r\n]+)')


def _extract_csrf_token(body: bytes, content_type: str) -> str:
    """Extrae el csrf_token del body sin consumir request.form().

    Usa parse_qs para URL-encoded y regex para multipart.
    Esto evita que BaseHTTPMiddleware consuma el body stream,
    permitiendo que FastAPI lo lea despues en el router.
    """
    try:
        if "multipart/form-data" in content_type:
            m = _MULTIPART_CSRF_RE.search(body)
            return m.group(1).decode("utf-8", errors="replace") if m else ""
        else:
            params = parse_qs(body.decode("utf-8", errors="replace"))
            values = params.get("csrf_token", [""])
            return values[0] if values else ""
    except Exception:
        return ""


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # Rutas públicas: no requieren auth
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            request.state.user = None
            return await call_next(request)

        # Leer cookie de sesión
        cookie = request.cookies.get(COOKIE_NAME)
        if not cookie:
            return RedirectResponse("/login", status_code=303)

        data = decode_session_cookie(cookie)
        if not data:
            response = RedirectResponse("/login", status_code=303)
            response.delete_cookie(COOKIE_NAME)
            return response

        # Buscar usuario en BD y cargar info de local en una sola sesion
        db = None
        try:
            db = SessionLocal()
            user = db.query(models.Usuario).filter(
                models.Usuario.id == data["user_id"],
                models.Usuario.activo == True
            ).first()

            if not user:
                response = RedirectResponse("/login", status_code=303)
                response.delete_cookie(COOKIE_NAME)
                return response

            # Inyectar usuario en request
            request.state.user = user

            # Inyectar local_id y local_name en request.state
            if user.rol == "SUPERADMIN":
                selected = request.cookies.get(SELECTED_LOCAL_COOKIE)
                sel_id = decode_selected_local(selected)
                request.state.selected_local_id = sel_id
                request.state.local_id = sel_id

                _locales = db.query(models.Local).filter(
                    models.Local.activo == True
                ).order_by(models.Local.nombre).all()
                request.state.all_locales = [
                    {"id": l.id, "nombre": l.nombre, "codigo": l.codigo}
                    for l in _locales
                ]
                request.state.local_name = None
                if sel_id:
                    for l in _locales:
                        if l.id == sel_id:
                            request.state.local_name = l.nombre
                            break
            else:
                request.state.local_id = user.local_id
                request.state.selected_local_id = None
                request.state.all_locales = []
                request.state.local_name = None
                if user.local_id:
                    _lo = db.query(models.Local).filter(
                        models.Local.id == user.local_id
                    ).first()
                    if _lo:
                        request.state.local_name = _lo.nombre
        except (OperationalError, Exception):
            return RedirectResponse(
                "/login?error=Error+de+conexion+a+la+base+de+datos.+Verifica+que+PostgreSQL+este+activo.",
                status_code=303,
            )
        finally:
            if db:
                db.close()

        # Validar CSRF en peticiones POST (excepto en tests y rutas exentas)
        if request.method == "POST" and not _TESTING:
            if not any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES):
                # Leer body bytes (se cachean en request._body, disponible para el router)
                body = await request.body()
                content_type = request.headers.get("content-type", "")
                csrf_token = _extract_csrf_token(body, content_type)
                if not validate_csrf_token(csrf_token, cookie):
                    return Response("CSRF token inválido", status_code=403)

        try:
            response = await call_next(request)
        except Exception as e:
            if "OperationalError" in type(e).__name__ or "connection" in str(e).lower():
                return RedirectResponse(
                    "/login?error=Error+de+conexion+a+la+base+de+datos.+Verifica+que+PostgreSQL+este+activo.",
                    status_code=303,
                )
            raise

        # Inyectar cabeceras de seguridad en todas las respuestas
        if _SECURITY_HEADERS_ENABLED:
            for nombre, valor in _SECURITY_HEADERS.items():
                response.headers[nombre] = valor
            if _IS_PRODUCTION:
                response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        return response
