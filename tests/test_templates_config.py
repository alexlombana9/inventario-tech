"""Tests para templates_config.py: filtros Jinja2, csrf_token y has_permiso."""
import pytest


class TestFormatoMoneda:
    """Lineas 14-18: filtro moneda."""

    def test_positive_integer(self):
        from templates_config import formato_moneda
        assert formato_moneda(1000) == "$1,000.00"

    def test_positive_float(self):
        from templates_config import formato_moneda
        assert formato_moneda(1234.56) == "$1,234.56"

    def test_zero(self):
        from templates_config import formato_moneda
        assert formato_moneda(0) == "$0.00"

    def test_large_number(self):
        from templates_config import formato_moneda
        assert formato_moneda(1000000) == "$1,000,000.00"

    def test_none_returns_fallback(self):
        """Linea 17-18: TypeError → retorna '$0.00'."""
        from templates_config import formato_moneda
        assert formato_moneda(None) == "$0.00"

    def test_string_returns_fallback(self):
        """Linea 17-18: ValueError → retorna '$0.00'."""
        from templates_config import formato_moneda
        assert formato_moneda("no_es_numero") == "$0.00"

    def test_negative_number(self):
        from templates_config import formato_moneda
        result = formato_moneda(-500.0)
        assert result == "$-500.00"


class TestFormatoNumero:
    """Lineas 21-27: filtro numero."""

    def test_integer_value(self):
        """Linea 23-24: valor entero → sin decimales."""
        from templates_config import formato_numero
        assert formato_numero(1000) == "1,000"

    def test_float_that_is_whole(self):
        """Linea 23-24: float == int → sin decimales."""
        from templates_config import formato_numero
        assert formato_numero(1000.0) == "1,000"

    def test_float_with_decimals(self):
        """Linea 25: float con decimales."""
        from templates_config import formato_numero
        assert formato_numero(1234.56) == "1,234.56"

    def test_zero(self):
        from templates_config import formato_numero
        assert formato_numero(0) == "0"

    def test_none_returns_fallback(self):
        """Linea 26-27: TypeError → retorna '0'."""
        from templates_config import formato_numero
        assert formato_numero(None) == "0"

    def test_string_returns_fallback(self):
        """Linea 26-27: ValueError → retorna '0'."""
        from templates_config import formato_numero
        assert formato_numero("texto") == "0"

    def test_large_integer(self):
        from templates_config import formato_numero
        assert formato_numero(5000000) == "5,000,000"


class TestHasPermiso:
    """Lineas 34-39: _has_permiso global de templates."""

    def test_none_user_returns_false(self):
        """Linea 36-37: usuario None → False."""
        from templates_config import _has_permiso
        assert _has_permiso(None, "productos") is False

    def test_admin_has_any_permiso(self, db):
        """ADMIN siempre tiene permisos."""
        from tests.conftest import _make_user
        from templates_config import _has_permiso
        admin = _make_user(db, "adm_tpl", "pass1234", "Admin Tpl", "ADMIN")
        assert _has_permiso(admin, "productos") is True
        assert _has_permiso(admin, "cualquier_cosa") is True

    def test_vendedor_has_ventas_pos(self, db):
        from tests.conftest import _make_user
        from templates_config import _has_permiso
        vendedor = _make_user(db, "vend_tpl", "pass1234", "Vend Tpl", "VENDEDOR")
        assert _has_permiso(vendedor, "ventas_pos") is True

    def test_vendedor_lacks_inventario(self, db):
        from tests.conftest import _make_user
        from templates_config import _has_permiso
        vendedor = _make_user(db, "vend_tpl2", "pass1234", "Vend Tpl2", "VENDEDOR")
        assert _has_permiso(vendedor, "inventario") is False


class TestCsrfToken:
    """Lineas 42-48: _csrf_token global de templates."""

    def test_no_cookie_returns_empty_string(self):
        """Linea 46-47: sin cookie → retorna ''."""
        from templates_config import _csrf_token
        from starlette.requests import Request
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        result = _csrf_token(request)
        assert result == ""

    def test_with_valid_cookie_returns_token(self):
        """Linea 48: con cookie presente → retorna token CSRF no vacio."""
        from templates_config import _csrf_token
        from auth import COOKIE_NAME
        from starlette.requests import Request
        headers = [(b"cookie", f"{COOKIE_NAME}=mi_cookie_de_sesion".encode())]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
        }
        request = Request(scope)
        token = _csrf_token(request)
        assert token != ""
        assert isinstance(token, str)
        assert len(token) > 10


class TestTemplatesJinja2Filters:
    """Verifica que los filtros estan registrados en el entorno de Jinja2."""

    def test_moneda_filter_registered(self):
        from templates_config import templates, formato_moneda
        assert "moneda" in templates.env.filters
        assert templates.env.filters["moneda"] is formato_moneda

    def test_numero_filter_registered(self):
        from templates_config import templates, formato_numero
        assert "numero" in templates.env.filters
        assert templates.env.filters["numero"] is formato_numero

    def test_has_permiso_global_registered(self):
        from templates_config import templates, _has_permiso
        assert "has_permiso" in templates.env.globals
        assert templates.env.globals["has_permiso"] is _has_permiso

    def test_csrf_token_global_registered(self):
        from templates_config import templates, _csrf_token
        assert "csrf_token" in templates.env.globals
        assert templates.env.globals["csrf_token"] is _csrf_token

    def test_templates_instance_exists(self):
        """Linea 7: el objeto templates se inicializa correctamente."""
        from templates_config import templates
        from fastapi.templating import Jinja2Templates
        assert isinstance(templates, Jinja2Templates)
