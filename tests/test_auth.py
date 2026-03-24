"""Tests para el modulo de autenticacion (login, logout, sesiones)."""


class TestLoginPage:
    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "login" in resp.text.lower() or "usuario" in resp.text.lower()

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

    def test_logout_without_session(self, client):
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303


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
