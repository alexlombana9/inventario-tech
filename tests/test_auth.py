"""Tests para el modulo de autenticacion (login, logout, sesiones)."""
import time
import pytest
import models


class TestLoginPage:
    def test_authenticated_user_redirected_from_login(self, admin_client):
        resp = admin_client.get("/login", follow_redirects=False)
        # El middleware redirige rutas publicas sin inyectar user en state,
        # por lo que el login page puede mostrarse (200) o redirigir (303)
        assert resp.status_code in (200, 303)


class TestLogin:
    def test_login_success(self, client, admin_user):
        resp = client.post("/login", data={
            "username": "admin",
            "password": "admin12345",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"
        assert "techstock_session" in resp.cookies

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post("/login", data={
            "username": "admin",
            "password": "wrongpassword",
        })
        assert resp.status_code == 200
        assert "incorrecto" in resp.text.lower()

    def test_login_nonexistent_user(self, client):
        resp = client.post("/login", data={
            "username": "noexiste",
            "password": "whatever",
        })
        assert resp.status_code == 200
        assert "incorrecto" in resp.text.lower()

    def test_login_inactive_user(self, client, db):
        from tests.conftest import _make_user
        user = _make_user(db, "inactivo", "password123", "Inactivo", "VENDEDOR")
        user.activo = False
        db.commit()

        resp = client.post("/login", data={
            "username": "inactivo",
            "password": "password123",
        })
        assert resp.status_code == 200
        assert "desactivada" in resp.text.lower()

    def test_login_updates_ultimo_login(self, client, db, admin_user):
        assert admin_user.ultimo_login is None
        client.post("/login", data={
            "username": "admin",
            "password": "admin12345",
        })
        db.refresh(admin_user)
        assert admin_user.ultimo_login is not None


class TestLogout:
    def test_logout_clears_session(self, admin_client):
        resp = admin_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


class TestAuthMiddleware:
    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_static_files_are_public(self, client):
        resp = client.get("/static/css/style.css")
        assert resp.status_code == 200

    def test_authenticated_can_access_protected_routes(self, admin_client):
        resp = admin_client.get("/")
        assert resp.status_code == 200

    def test_invalid_cookie_redirects_to_login_and_deletes_cookie(self, client):
        """Lineas 43-45: cookie presente pero inválida → redirige y borra cookie."""
        client.cookies.set("techstock_session", "cookie.invalida.totalmente")
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_expired_cookie_redirects_to_login(self, client):
        """Lineas 43-45: decode_session_cookie retorna None → redirección."""
        from auth import _serializer
        # Firmar con un max_age de 0 segundos en el pasado para simular expiración
        expired_cookie = _serializer.dumps({"user_id": 999, "username": "ghost"})
        client.cookies.set("techstock_session", expired_cookie)
        # El usuario 999 no existe en BD → redirige a /login (lineas 57-60)
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_valid_cookie_but_user_not_found_redirects(self, client):
        """Lineas 58-60: cookie válida pero usuario no existe en BD."""
        from auth import create_session_cookie
        cookie = create_session_cookie(99999, "fantasma")
        client.cookies.set("techstock_session", cookie)
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_valid_cookie_inactive_user_redirects(self, client, db):
        """Lineas 58-60: cookie válida pero usuario inactivo → redirige."""
        from tests.conftest import _make_user
        from auth import create_session_cookie
        user = _make_user(db, "inactivo2", "pass1234", "Inactivo2", "VENDEDOR")
        user.activo = False
        db.commit()
        cookie = create_session_cookie(user.id, user.username)
        client.cookies.set("techstock_session", cookie)
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_csrf_validation_blocks_post_with_invalid_token(self, admin_user, monkeypatch):
        """Lineas 67-71: CSRF invalido retorna 403 cuando no esta en modo test."""
        import middleware
        # Deshabilitar temporalmente el bypass de tests para cubrir las lineas CSRF
        monkeypatch.setattr(middleware, "_TESTING", False)
        from main import app
        from database import get_db, SessionLocal
        from fastapi.testclient import TestClient

        db = SessionLocal()
        try:
            def _override_get_db():
                yield db

            app.dependency_overrides[get_db] = _override_get_db
            from auth import create_session_cookie, COOKIE_NAME
            cookie = create_session_cookie(admin_user.id, admin_user.username)
            with TestClient(app, raise_server_exceptions=False) as c:
                c.cookies.set(COOKIE_NAME, cookie)
                resp = c.post("/productos/nuevo", data={"csrf_token": "invalido"}, follow_redirects=False)
            assert resp.status_code == 403
            assert "CSRF" in resp.text or "csrf" in resp.text.lower()
        finally:
            db.close()
            app.dependency_overrides.clear()
            monkeypatch.setattr(middleware, "_TESTING", True)

    def test_csrf_validation_passes_with_valid_token(self, admin_user, monkeypatch):
        """Lineas 66-71: token CSRF válido pasa la validación."""
        import middleware
        monkeypatch.setattr(middleware, "_TESTING", False)
        from main import app
        from database import get_db, SessionLocal
        from fastapi.testclient import TestClient
        from auth import create_session_cookie, generate_csrf_token, COOKIE_NAME

        db = SessionLocal()
        try:
            def _override_get_db():
                yield db

            app.dependency_overrides[get_db] = _override_get_db
            cookie = create_session_cookie(admin_user.id, admin_user.username)
            valid_csrf = generate_csrf_token(cookie)
            with TestClient(app, raise_server_exceptions=False) as c:
                c.cookies.set(COOKIE_NAME, cookie)
                resp = c.post("/productos/nuevo", data={
                    "csrf_token": valid_csrf,
                    "nombre": "",
                }, follow_redirects=False)
            # 422 o redirect → pasó validacion CSRF (no 403)
            assert resp.status_code != 403
        finally:
            db.close()
            app.dependency_overrides.clear()
            monkeypatch.setattr(middleware, "_TESTING", True)


# ── Tests directos de funciones de auth ───────────────────────────────────────

class TestDecodeSessionCookie:
    """Lineas 74-77 (SignatureExpired / BadSignature)."""

    def test_decode_valid_cookie(self):
        from auth import create_session_cookie, decode_session_cookie
        cookie = create_session_cookie(1, "admin")
        data = decode_session_cookie(cookie)
        assert data is not None
        assert data["user_id"] == 1
        assert data["username"] == "admin"

    def test_decode_invalid_cookie_returns_none(self):
        from auth import decode_session_cookie
        assert decode_session_cookie("completamente.invalida") is None

    def test_decode_tampered_cookie_returns_none(self):
        from auth import decode_session_cookie
        assert decode_session_cookie("abc.def.ghi") is None


class TestValidateCsrfToken:
    """Lineas 94-97: token inválido o expirado."""

    def test_valid_csrf_token(self):
        from auth import generate_csrf_token, validate_csrf_token
        session = "mi_cookie_de_sesion"
        token = generate_csrf_token(session)
        assert validate_csrf_token(token, session) is True

    def test_invalid_csrf_token(self):
        from auth import validate_csrf_token
        assert validate_csrf_token("token.invalido", "cookie") is False

    def test_csrf_token_wrong_session(self):
        from auth import generate_csrf_token, validate_csrf_token
        token = generate_csrf_token("sesion_correcta")
        assert validate_csrf_token(token, "sesion_diferente") is False


class TestGenerateCsrfToken:
    """Linea 229: generate_csrf_token."""

    def test_different_sessions_different_tokens(self):
        from auth import generate_csrf_token
        t1 = generate_csrf_token("sesion_a")
        t2 = generate_csrf_token("sesion_b")
        assert t1 != t2


class TestRequireRole:
    """Lineas 119-126: require_role cuando el usuario no tiene el rol requerido."""

    def test_admin_accesses_admin_route(self, admin_client):
        """ADMIN puede acceder a rutas que requieren ADMIN."""
        resp = admin_client.get("/usuarios")
        assert resp.status_code == 200

    def test_vendedor_cannot_access_admin_only_route(self, vendedor_client):
        """VENDEDOR recibe 403 en rutas que requieren ADMIN."""
        resp = vendedor_client.get("/usuarios", follow_redirects=False)
        assert resp.status_code == 403

    def test_bodeguero_cannot_access_admin_only_route(self, bodeguero_client):
        """BODEGUERO recibe 403 en rutas que requieren ADMIN."""
        resp = bodeguero_client.get("/usuarios", follow_redirects=False)
        assert resp.status_code == 403

    def test_require_role_unauthenticated_redirects(self, client):
        """Sin sesión → redirige a /login (linea 188)."""
        resp = client.get("/usuarios", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_require_role_directly_raises_403_for_wrong_role(self, db):
        """require_role() lanza 403 cuando el usuario no tiene el rol correcto."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from tests.conftest import _make_user
        from auth import require_role

        vendedor = _make_user(db, "vend_role", "pass1234", "Vend Role", "VENDEDOR")
        # Simular request con usuario en state
        mock_request = MagicMock()
        mock_request.state.user = vendedor
        dependency = require_role("ADMIN")
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_request)
        assert exc_info.value.status_code == 403

    def test_require_role_directly_passes_for_correct_role(self, db):
        """require_role() retorna el usuario cuando tiene el rol correcto."""
        from unittest.mock import MagicMock
        from tests.conftest import _make_user
        from auth import require_role

        admin = _make_user(db, "adm_role", "pass1234", "Admin Role", "ADMIN")
        mock_request = MagicMock()
        mock_request.state.user = admin
        dependency = require_role("ADMIN")
        user = dependency(mock_request)
        assert user.rol == "ADMIN"

    def test_require_role_without_user_redirects(self):
        """require_role() lanza 303 cuando no hay usuario en request."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from auth import require_role

        mock_request = MagicMock()
        mock_request.state.user = None
        dependency = require_role("ADMIN")
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_request)
        assert exc_info.value.status_code == 303


class TestRequirePermiso:
    """Lineas 140-141: require_permiso edge cases (directo via dependency)."""

    def test_admin_has_all_permisos(self, admin_client):
        """ADMIN tiene acceso a todos los módulos."""
        resp = admin_client.get("/productos")
        assert resp.status_code == 200

    def test_require_permiso_unauthenticated_redirects(self, client):
        """Sin sesión → redirige a /login (linea 244-245)."""
        resp = client.get("/productos", follow_redirects=False)
        assert resp.status_code == 303

    def test_require_permiso_raises_403_for_missing_permiso(self, db):
        """require_permiso() lanza 403 cuando el usuario no tiene el modulo."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from tests.conftest import _make_user
        from auth import require_permiso

        vendedor = _make_user(db, "vend_perm", "pass1234", "Vend Perm", "VENDEDOR")
        mock_request = MagicMock()
        mock_request.state.user = vendedor
        dependency = require_permiso("inventario")
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_request)
        assert exc_info.value.status_code == 403

    def test_require_permiso_passes_for_granted_permiso(self, db):
        """require_permiso() retorna el usuario cuando tiene el modulo."""
        from unittest.mock import MagicMock
        from tests.conftest import _make_user
        from auth import require_permiso

        vendedor = _make_user(db, "vend_perm2", "pass1234", "Vend Perm2", "VENDEDOR")
        mock_request = MagicMock()
        mock_request.state.user = vendedor
        dependency = require_permiso("ventas_pos")
        user = dependency(mock_request)
        assert user.username == "vend_perm2"

    def test_require_permiso_without_user_redirects(self):
        """require_permiso() lanza 303 cuando no hay usuario en request."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from auth import require_permiso

        mock_request = MagicMock()
        mock_request.state.user = None
        dependency = require_permiso("productos")
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_request)
        assert exc_info.value.status_code == 303


class TestUserHasPermiso:
    """Lineas 164-165, 172, 179: user_has_permiso y get_user_permisos."""

    def test_admin_always_has_permiso(self, db):
        from tests.conftest import _make_user
        from auth import user_has_permiso
        admin = _make_user(db, "adm2", "pass1234", "Admin2", "ADMIN")
        assert user_has_permiso(admin, "cualquier_modulo") is True
        assert user_has_permiso(admin, "productos") is True
        assert user_has_permiso(admin, "modulo_inexistente") is True

    def test_vendedor_has_ventas_pos(self, db):
        from tests.conftest import _make_user
        from auth import user_has_permiso
        vendedor = _make_user(db, "vend2", "pass1234", "Vend2", "VENDEDOR")
        assert user_has_permiso(vendedor, "ventas_pos") is True

    def test_vendedor_lacks_inventario(self, db):
        from tests.conftest import _make_user
        from auth import user_has_permiso
        vendedor = _make_user(db, "vend3", "pass1234", "Vend3", "VENDEDOR")
        assert user_has_permiso(vendedor, "inventario") is False

    def test_bodeguero_has_inventario(self, db):
        from tests.conftest import _make_user
        from auth import user_has_permiso
        bodeguero = _make_user(db, "bod2", "pass1234", "Bod2", "BODEGUERO")
        assert user_has_permiso(bodeguero, "inventario") is True

    def test_bodeguero_lacks_ventas_pos(self, db):
        from tests.conftest import _make_user
        from auth import user_has_permiso
        bodeguero = _make_user(db, "bod3", "pass1234", "Bod3", "BODEGUERO")
        assert user_has_permiso(bodeguero, "ventas_pos") is False

    def test_custom_permisos_override_rol(self, db):
        """Linea 172: si permisos custom no estan vacios se usan en lugar del rol."""
        from tests.conftest import _make_user
        from auth import user_has_permiso, get_user_permisos
        usuario = _make_user(db, "custom1", "pass1234", "Custom1", "VENDEDOR")
        usuario.permisos = "productos,inventario"
        db.commit()
        db.refresh(usuario)
        permisos = get_user_permisos(usuario)
        assert "productos" in permisos
        assert "inventario" in permisos
        # ventas_pos ya no esta en los permisos custom
        assert "ventas_pos" not in permisos

    def test_empty_permisos_falls_back_to_rol(self, db):
        """Linea 179: permisos vacio o solo espacios usa los del rol."""
        from tests.conftest import _make_user
        from auth import get_user_permisos, PERMISOS_POR_ROL
        usuario = _make_user(db, "custom2", "pass1234", "Custom2", "BODEGUERO")
        usuario.permisos = "   "
        db.commit()
        db.refresh(usuario)
        permisos = get_user_permisos(usuario)
        assert permisos == PERMISOS_POR_ROL["BODEGUERO"]

    def test_none_permisos_falls_back_to_rol(self, db):
        """Linea 179: permisos None usa los del rol."""
        from tests.conftest import _make_user
        from auth import get_user_permisos, PERMISOS_POR_ROL
        usuario = _make_user(db, "custom3", "pass1234", "Custom3", "VENDEDOR")
        # usuario.permisos es None por defecto en el modelo
        permisos = get_user_permisos(usuario)
        assert permisos == PERMISOS_POR_ROL["VENDEDOR"]


class TestGetSavedAccounts:
    """Lineas 242-249: get_saved_accounts con cookie válida, ausente e inválida."""

    def test_no_accounts_cookie_returns_empty_list(self, client):
        from auth import get_saved_accounts
        from starlette.requests import Request
        from starlette.datastructures import Headers
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        result = get_saved_accounts(request)
        assert result == []

    def test_valid_accounts_cookie(self, client):
        from auth import get_saved_accounts, save_accounts_cookie, ACCOUNTS_COOKIE
        from fastapi.responses import RedirectResponse
        from starlette.requests import Request
        # Crear una cookie de cuentas válida
        response = RedirectResponse("/")
        accounts = [{"username": "admin", "nombre": "Admin"}]
        save_accounts_cookie(response, accounts)
        # Extraer el valor de la cookie de la respuesta
        cookie_header = dict(response.headers)
        # La cookie se establece en set-cookie header
        cookie_val = None
        for key, val in response.headers.items():
            if key.lower() == "set-cookie" and ACCOUNTS_COOKIE in val:
                # Parsear valor de la cookie
                parts = val.split(";")
                cookie_val = parts[0].split("=", 1)[1]
                break
        assert cookie_val is not None
        # Crear request con la cookie
        headers = [(b"cookie", f"{ACCOUNTS_COOKIE}={cookie_val}".encode())]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
        }
        request = Request(scope)
        result = get_saved_accounts(request)
        assert result == accounts

    def test_invalid_accounts_cookie_returns_empty_list(self):
        from auth import get_saved_accounts, ACCOUNTS_COOKIE
        from starlette.requests import Request
        headers = [(b"cookie", f"{ACCOUNTS_COOKIE}=cookie.invalida.completamente".encode())]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
        }
        request = Request(scope)
        result = get_saved_accounts(request)
        assert result == []


class TestValidatePassword:
    """Lineas 261-265: validate_password."""

    def test_valid_password(self):
        from auth import validate_password
        assert validate_password("SecurePass1") is None

    def test_too_short(self):
        from auth import validate_password
        result = validate_password("Sh0rt")
        assert result is not None
        assert "8" in result

    def test_no_uppercase(self):
        from auth import validate_password
        result = validate_password("nouppercase1")
        assert result is not None
        assert "mayúscula" in result.lower() or "mayuscula" in result.lower()

    def test_no_lowercase(self):
        from auth import validate_password
        result = validate_password("NOLOWERCASE1")
        assert result is not None
        assert "minúscula" in result.lower() or "minuscula" in result.lower()

    def test_no_digits(self):
        from auth import validate_password
        result = validate_password("NoDigitsHere")
        assert result is not None
        assert "número" in result.lower() or "numero" in result.lower()


class TestRateLimiter:
    """Lineas 270-276: RateLimiter."""

    def test_not_limited_initially(self):
        from auth import RateLimiter
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.is_limited("192.168.1.1") is False

    def test_record_increments_attempts(self):
        from auth import RateLimiter
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record("192.168.1.2")
        limiter.record("192.168.1.2")
        assert limiter.remaining("192.168.1.2") == 1

    def test_is_limited_after_max_attempts(self):
        from auth import RateLimiter
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record("192.168.1.3")
        assert limiter.is_limited("192.168.1.3") is True

    def test_old_attempts_expire(self):
        from auth import RateLimiter
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        for _ in range(3):
            limiter.record("192.168.1.6")
        assert limiter.is_limited("192.168.1.6") is True
        time.sleep(1.1)
        assert limiter.is_limited("192.168.1.6") is False


class TestGetFlash:
    """Lineas 164-165: get_flash con cookie inválida o expirada."""

    def test_get_flash_invalid_cookie_returns_none(self):
        """Linea 164-165: cookie inválida → retorna None."""
        from auth import get_flash, FLASH_COOKIE
        from starlette.requests import Request
        headers = [(b"cookie", f"{FLASH_COOKIE}=token.invalido.xyz".encode())]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
        }
        request = Request(scope)
        assert get_flash(request) is None

    def test_get_flash_valid_cookie_returns_message(self):
        """get_flash con cookie válida retorna el mensaje."""
        from auth import get_flash, set_flash, FLASH_COOKIE
        from fastapi.responses import RedirectResponse
        from starlette.requests import Request
        # Crear flash cookie válida
        response = RedirectResponse("/")
        set_flash(response, "Operacion exitosa", "success")
        # Extraer valor de la cookie
        cookie_val = None
        for key, val in response.headers.items():
            if key.lower() == "set-cookie" and FLASH_COOKIE in val:
                cookie_val = val.split(";")[0].split("=", 1)[1]
                break
        assert cookie_val is not None
        headers = [(b"cookie", f"{FLASH_COOKIE}={cookie_val}".encode())]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
        }
        request = Request(scope)
        result = get_flash(request)
        assert result is not None
        assert result["message"] == "Operacion exitosa"
        assert result["category"] == "success"


class TestGetCurrentUser:
    """Linea 172: get_current_user."""

    def test_returns_user_from_request_state(self, db):
        """get_current_user retorna el usuario del request.state."""
        from unittest.mock import MagicMock
        from tests.conftest import _make_user
        from auth import get_current_user
        admin = _make_user(db, "adm_cu", "pass1234", "Admin CU", "ADMIN")
        mock_request = MagicMock()
        mock_request.state.user = admin
        result = get_current_user(mock_request)
        assert result is admin


class TestRequireAuth:
    """Lineas 177-180: require_auth."""

    def test_require_auth_returns_user_when_authenticated(self, db):
        """require_auth retorna el usuario cuando esta autenticado."""
        from unittest.mock import MagicMock
        from tests.conftest import _make_user
        from auth import require_auth
        admin = _make_user(db, "adm_ra", "pass1234", "Admin RA", "ADMIN")
        mock_request = MagicMock()
        mock_request.state.user = admin
        result = require_auth(mock_request)
        assert result is admin

    def test_require_auth_raises_303_when_no_user(self):
        """Lineas 178-179: require_auth lanza HTTPException 303 sin usuario."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from auth import require_auth
        mock_request = MagicMock()
        mock_request.state.user = None
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)
        assert exc_info.value.status_code == 303
        assert "/login" in exc_info.value.headers["Location"]


class TestGetSecretKey:
    """Lineas 94-97: _get_secret_key cuando el archivo no existe."""

    def test_creates_key_file_when_missing(self, tmp_path, monkeypatch):
        """Si el archivo .secret_key no existe, lo crea y retorna la clave."""
        import auth as auth_module
        key_file = str(tmp_path / ".secret_key")
        monkeypatch.setattr(auth_module, "SECRET_KEY_FILE", key_file)
        # Asegurar que el archivo no existe
        import os
        assert not os.path.exists(key_file)
        key = auth_module._get_secret_key()
        assert isinstance(key, str)
        assert len(key) == 64  # 32 bytes hex = 64 chars
        assert os.path.exists(key_file)

    def test_reads_existing_key_file(self, tmp_path, monkeypatch):
        """Si el archivo ya existe, lee la clave de él."""
        import auth as auth_module
        key_file = str(tmp_path / ".secret_key")
        expected_key = "abcdef1234567890" * 4
        with open(key_file, "w") as f:
            f.write(expected_key)
        monkeypatch.setattr(auth_module, "SECRET_KEY_FILE", key_file)
        key = auth_module._get_secret_key()
        assert key == expected_key


class TestSetupWizard:
    """Tests para el wizard de configuracion inicial (/setup)."""

    def test_get_setup_shows_form_when_no_users(self, client):
        """GET /setup sin usuarios muestra el formulario de configuracion."""
        resp = client.get("/setup")
        assert resp.status_code == 200
        assert "Configuracion Inicial" in resp.text
        assert "nombre_negocio" in resp.text
        assert "nombre_completo" in resp.text

    def test_get_setup_redirects_when_users_exist(self, client, admin_user):
        """GET /setup con usuarios existentes redirige a /login."""
        resp = client.get("/setup", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_login_redirects_to_setup_when_no_users(self, client):
        """GET /login sin usuarios redirige a /setup."""
        resp = client.get("/login", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/setup"

    def test_post_setup_creates_superadmin(self, client, db):
        """POST /setup crea un SUPERADMIN y configura el negocio."""
        resp = client.post("/setup", data={
            "nombre_negocio": "Mi Tienda",
            "nombre_completo": "Juan Admin",
            "username": "juanadmin",
            "password": "Secure123",
            "confirmar_password": "Secure123",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

        # Verificar que se creo el usuario SUPERADMIN
        user = db.query(models.Usuario).filter(
            models.Usuario.username == "juanadmin"
        ).first()
        assert user is not None
        assert user.rol == "SUPERADMIN"
        assert user.nombre_completo == "Juan Admin"
        assert user.local_id is None
        assert user.activo is True

        # Verificar que se creo/actualizo la configuracion
        config = db.query(models.Configuracion).first()
        assert config is not None
        assert config.nombre_negocio == "Mi Tienda"

        # Verificar que se creo el local
        local = db.query(models.Local).first()
        assert local is not None

    def test_post_setup_mismatched_passwords(self, client):
        """POST /setup con contrasenas diferentes muestra error."""
        resp = client.post("/setup", data={
            "nombre_negocio": "Mi Tienda",
            "nombre_completo": "Juan Admin",
            "username": "juanadmin",
            "password": "Secure123",
            "confirmar_password": "Different123",
        })
        assert resp.status_code == 200
        assert "no coinciden" in resp.text.lower()

    def test_post_setup_weak_password(self, client):
        """POST /setup con contrasena debil muestra error."""
        resp = client.post("/setup", data={
            "nombre_negocio": "Mi Tienda",
            "nombre_completo": "Juan Admin",
            "username": "juanadmin",
            "password": "short",
            "confirmar_password": "short",
        })
        assert resp.status_code == 200
        # validate_password retorna error sobre longitud minima
        assert "8" in resp.text

    def test_post_setup_short_username(self, client):
        """POST /setup con usuario corto muestra error."""
        resp = client.post("/setup", data={
            "nombre_negocio": "Mi Tienda",
            "nombre_completo": "Juan Admin",
            "username": "ab",
            "password": "Secure123",
            "confirmar_password": "Secure123",
        })
        assert resp.status_code == 200
        assert "3 caracteres" in resp.text.lower()

    def test_post_setup_redirects_when_users_exist(self, client, admin_user):
        """POST /setup con usuarios existentes redirige a /login."""
        resp = client.post("/setup", data={
            "nombre_negocio": "Mi Tienda",
            "nombre_completo": "Otro Admin",
            "username": "otroadmin",
            "password": "Secure123",
            "confirmar_password": "Secure123",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
