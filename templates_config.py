import os
import sys
from fastapi.templating import Jinja2Templates

# Resolve paths correctly for both dev and PyInstaller frozen mode
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
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


templates.env.globals["has_permiso"] = _has_permiso
templates.env.globals["csrf_token"] = _csrf_token
