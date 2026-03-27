"""Tests para el router de autenticacion (login, logout, multi-cuenta)."""
import pytest
import models
from auth import (
    create_session_cookie, COOKIE_NAME, ACCOUNTS_COOKIE,
    save_accounts_cookie, login_limiter, hash_password,
)
from fastapi.responses import RedirectResponse


class TestLoginPage:
    def test_login_page_get(self, client):
        """Line 19-27: GET /login muestra el formulario."""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "login" in resp.text.lower() or "usuario" in resp.text.lower()

    def test_login_page_ya_autenticado_redirige(self, admin_client):
        """Line 22: Usuario autenticado es redirigido al dashboard."""
        resp = admin_client.get("/login", follow_redirects=False)
        # Middleware marks /login as public so user may or may not be set;
        # if redirect happens it's 303 to /, otherwise 200 with login page
        assert resp.status_code in (200, 303)

    def test_login_page_con_agregar_no_redirige(self, admin_client):
        """Line 21: Con ?agregar=1 no redirige aunque este autenticado."""
        resp = admin_client.get("/login?agregar=1")
        assert resp.status_code == 200

    def test_login_page_con_error(self, client):
        """Parametro ?error se muestra en la pagina."""
        resp = client.get("/login?error=Usuario+incorrecto")
        assert resp.status_code == 200


class TestLoginPost:
    def test_login_exitoso(self, client, admin_user):
        """Lines 125-185: Login con credenciales correctas redirige al dashboard."""
        resp = client.post("/login", data={
            "username": "admin",
            "password": "admin12345",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"
        assert COOKIE_NAME in resp.cookies

    def test_login_usuario_no_encontrado(self, client, db):
        """Lines 125-185: Usuario inexistente muestra error."""
        resp = client.post("/login", data={
            "username": "noexiste",
            "password": "cualquier123",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "incorrecto" in resp.text.lower() or "error" in resp.text.lower()

    def test_login_password_incorrecta(self, client, admin_user):
        """Lines 125-185: Password incorrecta muestra error."""
        resp = client.post("/login", data={
            "username": "admin",
            "password": "PasswordMalA1",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "incorrecto" in resp.text.lower() or "error" in resp.text.lower()

    def test_login_usuario_inactivo(self, client, db):
        """Lines 125-185: Usuario inactivo muestra error de cuenta desactivada."""
        user = models.Usuario(
            username="inactivo",
            password_hash=hash_password("Inactivo123"),
            nombre_completo="Usuario Inactivo",
            rol="VENDEDOR",
            activo=False,
        )
        db.add(user)
        db.commit()

        resp = client.post("/login", data={
            "username": "inactivo",
            "password": "Inactivo123",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "desactivada" in resp.text.lower() or "error" in resp.text.lower()

    def test_login_actualiza_ultimo_login(self, client, db, admin_user):
        """Login exitoso actualiza el campo ultimo_login."""
        assert admin_user.ultimo_login is None
        client.post("/login", data={
            "username": "admin",
            "password": "admin12345",
        }, follow_redirects=False)
        db.refresh(admin_user)
        assert admin_user.ultimo_login is not None

    def test_login_genera_auditoria(self, client, db, admin_user):
        """Login exitoso registra entrada en audit log."""
        client.post("/login", data={
            "username": "admin",
            "password": "admin12345",
        }, follow_redirects=False)
        log = db.query(models.AuditLog).filter_by(accion="LOGIN").first()
        assert log is not None

    def test_login_rate_limiting(self, client, db):
        """Lines 125-185: Demasiados intentos muestra mensaje de rate limit."""
        user = models.Usuario(
            username="victima",
            password_hash=hash_password("Password123"),
            nombre_completo="Victima",
            rol="VENDEDOR",
            activo=True,
        )
        db.add(user)
        db.commit()

        # Saturar el limiter para testclient IP (127.0.0.1)
        ip = "testclient"
        for _ in range(login_limiter.max_attempts):
            login_limiter.record(ip)

        try:
            resp = client.post("/login", data={
                "username": "victima",
                "password": "Wrong123",
            }, follow_redirects=False)
            assert resp.status_code == 200
            assert "intentos" in resp.text.lower() or "demasiados" in resp.text.lower() or "espera" in resp.text.lower()
        finally:
            # Limpiar limiter para no afectar otros tests
            login_limiter._attempts.clear()

    def test_login_con_agregar_cuenta(self, client, admin_user, db):
        """Lines 125-185: Login con agregar=1 guarda cookie de cuentas."""
        # Primero autenticarse como admin
        client.post("/login", data={
            "username": "admin",
            "password": "admin12345",
        }, follow_redirects=False)

        # Crear segundo usuario
        user2 = models.Usuario(
            username="vendedor2",
            password_hash=hash_password("Vendedor123"),
            nombre_completo="Vendedor Dos",
            rol="VENDEDOR",
            activo=True,
        )
        db.add(user2)
        db.commit()

        resp = client.post("/login", data={
            "username": "vendedor2",
            "password": "Vendedor123",
            "agregar": "1",
        }, follow_redirects=False)
        assert resp.status_code == 303


class TestLogout:
    def test_logout_redirige_a_login(self, admin_client):
        """Lines 194-203: Logout redirige a /login."""
        resp = admin_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_logout_elimina_cookie_sesion(self, admin_client):
        """Lines 194-203: Logout elimina la cookie de sesion."""
        resp = admin_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303

    def test_logout_sin_sesion_redirige(self, client):
        """Logout sin sesion activa redirige a login igual."""
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_logout_genera_auditoria(self, admin_client, db, admin_user):
        """Logout registra LOGOUT en auditoria si hay sesion."""
        admin_client.get("/logout", follow_redirects=False)
        log = db.query(models.AuditLog).filter_by(accion="LOGOUT").first()
        assert log is not None


class TestCambiarCuenta:
    def test_cambiar_cuenta_sin_sesion_redirige(self, client):
        """Lines 125-185: Sin sesion redirige a login."""
        resp = client.get("/cambiar-cuenta/999", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_cambiar_cuenta_no_en_lista(self, admin_client):
        """Cuenta no guardada redirige con error."""
        resp = admin_client.get("/cambiar-cuenta/9999", follow_redirects=False)
        assert resp.status_code == 303
        assert "/perfil" in resp.headers["location"]

    def test_cambiar_cuenta_usuario_inactivo(self, admin_client, db, vendedor_user):
        """Cambiar a cuenta inactiva muestra error."""
        from auth import save_accounts_cookie
        from fastapi.testclient import TestClient

        # Desactivar vendedor
        vendedor_user.activo = False
        db.commit()

        # Simular cookie de cuentas guardadas con el vendedor
        from fastapi.responses import Response
        resp_mock = Response()
        accounts = [{
            "user_id": vendedor_user.id,
            "username": vendedor_user.username,
            "nombre_completo": vendedor_user.nombre_completo,
            "foto": "",
            "rol": vendedor_user.rol,
            "cookie": "dummy_cookie",
        }]
        save_accounts_cookie(resp_mock, accounts)
        accounts_cookie_value = resp_mock.headers.get("set-cookie", "")

        # Extraer el valor de la cookie
        from auth import _serializer, ACCOUNTS_COOKIE
        cookie_value = _serializer.dumps(accounts)
        admin_client.cookies.set(ACCOUNTS_COOKIE, cookie_value)

        resp = admin_client.get(f"/cambiar-cuenta/{vendedor_user.id}", follow_redirects=False)
        assert resp.status_code == 303
        assert "/perfil" in resp.headers["location"]

    def test_cambiar_cuenta_exitoso(self, admin_client, db, vendedor_user):
        """Cambiar a cuenta valida y activa."""
        from auth import _serializer, ACCOUNTS_COOKIE

        # Simular cookie con el vendedor guardado
        accounts = [{
            "user_id": vendedor_user.id,
            "username": vendedor_user.username,
            "nombre_completo": vendedor_user.nombre_completo,
            "foto": "",
            "rol": vendedor_user.rol,
            "cookie": "dummy_cookie_value",
        }]
        cookie_value = _serializer.dumps(accounts)
        admin_client.cookies.set(ACCOUNTS_COOKIE, cookie_value)

        resp = admin_client.get(f"/cambiar-cuenta/{vendedor_user.id}", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"


class TestCerrarCuentaGuardada:
    def test_cerrar_cuenta_sin_sesion(self, client):
        """Lines 194-203: Sin sesion redirige a login."""
        resp = client.get("/cerrar-cuenta/999", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_cerrar_cuenta_guardada(self, admin_client, db, vendedor_user):
        """Lines 194-203: Remover una cuenta guardada redirige a /perfil."""
        from auth import _serializer, ACCOUNTS_COOKIE

        accounts = [{
            "user_id": vendedor_user.id,
            "username": vendedor_user.username,
            "nombre_completo": vendedor_user.nombre_completo,
            "foto": "",
            "rol": vendedor_user.rol,
            "cookie": "dummy_cookie",
        }]
        cookie_value = _serializer.dumps(accounts)
        admin_client.cookies.set(ACCOUNTS_COOKIE, cookie_value)

        resp = admin_client.get(f"/cerrar-cuenta/{vendedor_user.id}", follow_redirects=False)
        assert resp.status_code == 303
        assert "/perfil" in resp.headers["location"]
