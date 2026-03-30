import os
import sys
from fastapi.templating import Jinja2Templates

# Resolve paths correctly for both dev and PyInstaller frozen mode
if getattr(sys, "frozen", False):  # pragma: no cover
    _BASE_DIR = os.path.dirname(sys.executable)  # pragma: no cover
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(_BASE_DIR, "templates"))


def formato_moneda(value):
    try:
        return f"${value:,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def formato_numero(value):
    try:
        if value == int(value):
            return f"{int(value):,}"
        return f"{value:,.2f}"
    except (TypeError, ValueError):
        return "0"


templates.env.filters["moneda"] = formato_moneda
templates.env.filters["numero"] = formato_numero


def _has_permiso(user, modulo):
    """Template helper to check if a user has access to a module."""
    if not user:
        return False
    from auth import user_has_permiso
    return user_has_permiso(user, modulo)


def _csrf_token(request):
    """Genera token CSRF para formularios."""
    from auth import generate_csrf_token, COOKIE_NAME
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not cookie:
        return ""
    return generate_csrf_token(cookie)


def _is_superadmin(user):
    """Template helper to check if user is SUPERADMIN."""
    if not user:
        return False
    return user.rol == "SUPERADMIN"


def _get_flash(request):
    """Lee flash message de la cookie (disponible en todas las paginas via base.html)."""
    from auth import get_flash
    return get_flash(request)


def _movimientos_hoy(request):
    """Retorna dict con conteo de entradas y salidas de inventario del dia actual.

    Filtra por local_id respetando multi-tenant. Se usa en el topbar de base.html.
    Usa una sola query agrupada en vez de 2 queries separadas.
    """
    import os
    if os.environ.get("TESTING") == "1":
        return {"entradas": 0, "salidas": 0}
    try:
        from database import SessionLocal
        from sqlalchemy import func
        from datetime import date, datetime
        import models

        user = getattr(request.state, "user", None)
        if not user:
            return {"entradas": 0, "salidas": 0}

        local_id = getattr(request.state, "local_id", None)
        db = SessionLocal()
        try:
            hoy_inicio = datetime.combine(date.today(), datetime.min.time())
            hoy_fin = datetime.combine(date.today(), datetime.max.time())

            # Query unica con GROUP BY en vez de 2 queries separadas
            q = db.query(
                models.MovimientoInventario.tipo,
                func.count(models.MovimientoInventario.id),
            ).filter(
                models.MovimientoInventario.tipo.in_(["ENTRADA", "SALIDA"]),
                models.MovimientoInventario.fecha >= hoy_inicio,
                models.MovimientoInventario.fecha <= hoy_fin,
            )
            if local_id is not None:
                q = q.filter(models.MovimientoInventario.local_id == local_id)

            result = {"entradas": 0, "salidas": 0}
            for tipo_mov, cnt in q.group_by(models.MovimientoInventario.tipo).all():
                if tipo_mov == "ENTRADA":
                    result["entradas"] = cnt
                elif tipo_mov == "SALIDA":
                    result["salidas"] = cnt
            return result
        finally:
            db.close()
    except Exception:
        return {"entradas": 0, "salidas": 0}


templates.env.globals["has_permiso"] = _has_permiso
templates.env.globals["csrf_token"] = _csrf_token
templates.env.globals["is_superadmin"] = _is_superadmin
templates.env.globals["get_flash"] = _get_flash
templates.env.globals["movimientos_hoy"] = _movimientos_hoy
