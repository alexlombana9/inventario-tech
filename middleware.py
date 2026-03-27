"""
Middleware de autenticación y CSRF para TechStock.
Valida la cookie de sesión en cada request y redirige a /login si no es válida.
Valida tokens CSRF en todas las peticiones POST.
"""
import os
import re
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from database import SessionLocal
from auth import decode_session_cookie, validate_csrf_token, COOKIE_NAME
import models


# Rutas que NO requieren autenticación
PUBLIC_PATHS = {"/login", "/favicon.ico"}
PUBLIC_PREFIXES = ("/static/",)

# Rutas POST exentas de CSRF (APIs JSON internas)
CSRF_EXEMPT_PREFIXES = ("/ventas/api/",)

# Deshabilitar CSRF en tests
_TESTING = os.environ.get("TESTING") == "1"

# Regex para extraer csrf_token de multipart body
_MULTIPART_CSRF_RE = re.compile(rb'name="csrf_token"\r?\n\r?\n([^\r\n-]+)')


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

        # Buscar usuario en BD
        db: Session = SessionLocal()
        try:
            user = db.query(models.Usuario).filter(
                models.Usuario.id == data["user_id"],
                models.Usuario.activo == True
            ).first()
        finally:
            db.close()

        if not user:
            response = RedirectResponse("/login", status_code=303)
            response.delete_cookie(COOKIE_NAME)
            return response

        # Inyectar usuario en request
        request.state.user = user

        # Inyectar local_id en request.state
        if user.rol == "SUPERADMIN":
            # SUPERADMIN puede seleccionar un local vía cookie
            selected = request.cookies.get("techstock_selected_local")
            if selected:
                try:
                    request.state.selected_local_id = int(selected)
                except (ValueError, TypeError):
                    request.state.selected_local_id = None
            else:
                request.state.selected_local_id = None
            request.state.local_id = request.state.selected_local_id
        else:
            request.state.local_id = user.local_id
            request.state.selected_local_id = None

        # Validar CSRF en peticiones POST (excepto en tests y rutas exentas)
        if request.method == "POST" and not _TESTING:
            if not any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES):
                # Leer body bytes (se cachean en request._body, disponible para el router)
                body = await request.body()
                content_type = request.headers.get("content-type", "")
                csrf_token = _extract_csrf_token(body, content_type)
                if not validate_csrf_token(csrf_token, cookie):
                    return Response("CSRF token inválido", status_code=403)

        return await call_next(request)
