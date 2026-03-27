"""
Middleware de autenticación y CSRF para TechStock.
Valida la cookie de sesión en cada request y redirige a /login si no es válida.
Valida tokens CSRF en todas las peticiones POST.
"""
import os
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

        # Validar CSRF en peticiones POST (excepto en tests y rutas exentas)
        if request.method == "POST" and not _TESTING:
            if not any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES):
                form = await request.form()
                csrf_token = form.get("csrf_token", "")
                if not validate_csrf_token(csrf_token, cookie):
                    return Response("CSRF token inválido", status_code=403)

        return await call_next(request)
