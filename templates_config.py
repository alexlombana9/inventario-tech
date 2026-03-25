from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


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


templates.env.globals["has_permiso"] = _has_permiso
