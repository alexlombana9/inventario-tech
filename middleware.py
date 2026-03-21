"""
Middleware de autenticación para TechStock.
Valida la cookie de sesión en cada request y redirige a /login si no es válida.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import SessionLocal
from auth import decode_session_cookie, COOKIE_NAME
import models


# Rutas que NO requieren autenticación
PUBLIC_PATHS = {"/login", "/favicon.ico"}
PUBLIC_PREFIXES = ("/static/",)


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

        return await call_next(request)
