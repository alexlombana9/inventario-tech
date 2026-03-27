"""Tests para el modulo de proveedores (CRUD, detalle)."""
import models


class TestListaProveedores:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/proveedores")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_proveedor):
        resp = admin_client.get("/proveedores")
        assert resp.status_code == 200
        assert "Proveedor Test" in resp.text

    def test_buscar_proveedor(self, admin_client, sample_proveedor):
        resp = admin_client.get("/proveedores?buscar=Proveedor")
        assert resp.status_code == 200
        assert "Proveedor Test" in resp.text

    def test_buscar_sin_resultados(self, admin_client, sample_proveedor):
        resp = admin_client.get("/proveedores?buscar=NoExiste")
        assert resp.status_code == 200


class TestCrearProveedor:
    def test_form_nuevo(self, admin_client):
        resp = admin_client.get("/proveedores/nuevo")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/proveedores/nuevo", data={
            "nombre": "Nuevo Prov",
            "contacto": "Maria Garcia",
            "telefono": "3112223333",
            "email": "maria@prov.com",
            "direccion": "Calle 123",
            "nit_ruc": "800555111",
        }, follow_redirects=False)
        assert resp.status_code == 303
        prov = db.query(models.Proveedor).filter_by(nombre="Nuevo Prov").first()
        assert prov is not None
        assert prov.email == "maria@prov.com"
        assert prov.activo is True


class TestEditarProveedor:
    def test_form_editar(self, admin_client, sample_proveedor):
        resp = admin_client.get(f"/proveedores/{sample_proveedor.id}/editar")
        assert resp.status_code == 200
        assert "Proveedor Test" in resp.text

    def test_editar_ok(self, admin_client, db, sample_proveedor):
        resp = admin_client.post(f"/proveedores/{sample_proveedor.id}/editar", data={
            "nombre": "Proveedor Actualizado",
            "contacto": "Pedro",
            "telefono": "555",
            "email": "nuevo@email.com",
            "direccion": "Nueva dir",
            "nit_ruc": "111",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_proveedor)
        assert sample_proveedor.nombre == "Proveedor Actualizado"

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.get("/proveedores/9999/editar", follow_redirects=False)
        assert resp.status_code == 303

    def test_post_editar_inexistente(self, admin_client):
        """Cubre linea 100: POST editar proveedor que no existe."""
        resp = admin_client.post("/proveedores/9999/editar", data={
            "nombre": "No Existe",
            "contacto": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "nit_ruc": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarProveedor:
    def test_eliminar_soft_delete(self, admin_client, db, sample_proveedor):
        resp = admin_client.post(
            f"/proveedores/{sample_proveedor.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_proveedor)
        assert sample_proveedor.activo is False

    def test_eliminar_inexistente(self, admin_client):
        """Cubre linea 123: POST eliminar proveedor que no existe."""
        resp = admin_client.post(
            "/proveedores/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestDetalleProveedor:
    def test_detalle_ok(self, admin_client, sample_proveedor):
        resp = admin_client.get(f"/proveedores/{sample_proveedor.id}/detalle")
        assert resp.status_code == 200
        assert "Proveedor Test" in resp.text

    def test_detalle_inexistente(self, admin_client):
        resp = admin_client.get("/proveedores/9999/detalle", follow_redirects=False)
        assert resp.status_code == 303
