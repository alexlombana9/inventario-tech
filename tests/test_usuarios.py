"""Tests para el modulo de gestion de usuarios (CRUD, roles)."""
import models


class TestListaUsuarios:
    def test_lista_admin(self, admin_client, admin_user):
        resp = admin_client.get("/usuarios")
        assert resp.status_code == 200
        assert "Admin Test" in resp.text

    def test_lista_buscar(self, admin_client, admin_user):
        resp = admin_client.get("/usuarios?buscar=admin")
        assert resp.status_code == 200

    def test_filtro_por_rol(self, admin_client, admin_user):
        """Line 40: Filtrar usuarios por rol."""
        resp = admin_client.get("/usuarios?rol=ADMIN")
        assert resp.status_code == 200

    def test_filtro_por_estado_activo(self, admin_client, admin_user):
        """Lines 42-43: Filtrar usuarios activos."""
        resp = admin_client.get("/usuarios?estado=activo")
        assert resp.status_code == 200

    def test_filtro_por_estado_inactivo(self, admin_client, admin_user):
        """Lines 44-45: Filtrar usuarios inactivos."""
        resp = admin_client.get("/usuarios?estado=inactivo")
        assert resp.status_code == 200

    def test_vendedor_no_puede_ver_lista(self, vendedor_client):
        resp = vendedor_client.get("/usuarios", follow_redirects=False)
        assert resp.status_code in (303, 403)


class TestCrearUsuario:
    def test_form_nuevo(self, admin_client):
        resp = admin_client.get("/usuarios/nuevo")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/usuarios/nuevo", data={
            "username": "nuevo_user",
            "password": "Password1234",
            "nombre_completo": "Nuevo Usuario",
            "rol": "VENDEDOR",
        }, follow_redirects=False)
        assert resp.status_code == 303
        user = db.query(models.Usuario).filter_by(username="nuevo_user").first()
        assert user is not None
        assert user.rol == "VENDEDOR"
        assert user.activo is True

    def test_crear_username_duplicado(self, admin_client, admin_user):
        resp = admin_client.post("/usuarios/nuevo", data={
            "username": "admin",
            "password": "Password1234",
            "nombre_completo": "Duplicado",
            "rol": "VENDEDOR",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_crear_password_corta(self, admin_client):
        resp = admin_client.post("/usuarios/nuevo", data={
            "username": "shortpw",
            "password": "123",
            "nombre_completo": "Short PW",
            "rol": "VENDEDOR",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_crear_password_minimo_8(self, admin_client):
        resp = admin_client.post("/usuarios/nuevo", data={
            "username": "sevenpw",
            "password": "1234567",
            "nombre_completo": "Seven chars",
            "rol": "VENDEDOR",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_vendedor_no_puede_crear(self, vendedor_client):
        resp = vendedor_client.post("/usuarios/nuevo", data={
            "username": "hack",
            "password": "Hackpass1234",
            "nombre_completo": "Hacker",
            "rol": "ADMIN",
        }, follow_redirects=False)
        assert resp.status_code in (303, 403)


class TestEditarUsuario:
    def test_form_editar(self, admin_client, vendedor_user):
        resp = admin_client.get(f"/usuarios/{vendedor_user.id}/editar")
        assert resp.status_code == 200

    def test_editar_ok(self, admin_client, db, vendedor_user):
        resp = admin_client.post(f"/usuarios/{vendedor_user.id}/editar", data={
            "nombre_completo": "Vendedor Actualizado",
            "rol": "BODEGUERO",
            "password": "",
            "activo": "on",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(vendedor_user)
        assert vendedor_user.nombre_completo == "Vendedor Actualizado"
        assert vendedor_user.rol == "BODEGUERO"

    def test_editar_con_password(self, admin_client, db, vendedor_user):
        old_hash = vendedor_user.password_hash
        admin_client.post(f"/usuarios/{vendedor_user.id}/editar", data={
            "nombre_completo": vendedor_user.nombre_completo,
            "rol": vendedor_user.rol,
            "password": "NuevaPass123",
            "activo": "on",
        })
        db.refresh(vendedor_user)
        assert vendedor_user.password_hash != old_hash

    def test_no_puede_desactivarse_a_si_mismo(self, admin_client, admin_user):
        resp = admin_client.post(f"/usuarios/{admin_user.id}/editar", data={
            "nombre_completo": "Admin",
            "rol": "ADMIN",
            "password": "",
            "activo": "off",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.get("/usuarios/9999/editar", follow_redirects=False)
        assert resp.status_code == 303

    def test_editar_post_inexistente(self, admin_client):
        """Line 40: POST editar usuario no encontrado redirige con error."""
        resp = admin_client.post("/usuarios/9999/editar", data={
            "nombre_completo": "Nadie",
            "rol": "VENDEDOR",
            "password": "",
            "activo": "on",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_editar_password_invalida(self, admin_client, vendedor_user):
        """Lines 42-45: Password invalida en editar redirige con error."""
        resp = admin_client.post(f"/usuarios/{vendedor_user.id}/editar", data={
            "nombre_completo": vendedor_user.nombre_completo,
            "rol": "VENDEDOR",
            "password": "corta",
            "activo": "on",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarUsuario:
    def test_eliminar_soft_delete(self, admin_client, db, vendedor_user):
        resp = admin_client.post(
            f"/usuarios/{vendedor_user.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(vendedor_user)
        assert vendedor_user.activo is False

    def test_no_puede_eliminarse_a_si_mismo(self, admin_client, admin_user):
        resp = admin_client.post(
            f"/usuarios/{admin_user.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_eliminar_inexistente(self, admin_client):
        resp = admin_client.post(
            "/usuarios/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
