"""Tests para el modulo de clientes (CRUD, detalle)."""
import models


class TestListaClientes:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/clientes")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_cliente):
        resp = admin_client.get("/clientes")
        assert resp.status_code == 200
        assert "Cliente Test" in resp.text

    def test_buscar_por_nombre(self, admin_client, sample_cliente):
        resp = admin_client.get("/clientes?buscar=Cliente")
        assert resp.status_code == 200
        assert "Cliente Test" in resp.text

    def test_buscar_por_documento(self, admin_client, sample_cliente):
        resp = admin_client.get("/clientes?buscar=1234567890")
        assert resp.status_code == 200
        assert "Cliente Test" in resp.text

    def test_filtro_tipo_documento(self, admin_client, sample_cliente):
        """Cubre linea 34: filtro por tipo_documento en lista clientes."""
        resp = admin_client.get("/clientes?tipo_documento=CC")
        assert resp.status_code == 200
        assert "Cliente Test" in resp.text

    def test_filtro_tipo_documento_sin_resultados(self, admin_client, sample_cliente):
        """Cubre linea 34: tipo_documento que no tiene clientes."""
        resp = admin_client.get("/clientes?tipo_documento=PASAPORTE")
        assert resp.status_code == 200


class TestCrearCliente:
    def test_form_nuevo(self, admin_client):
        resp = admin_client.get("/clientes/nuevo")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/clientes/nuevo", data={
            "nombre": "Nuevo Cliente",
            "tipo_documento": "CC",
            "documento": "5555555555",
            "telefono": "3001111111",
            "email": "nuevo@cli.com",
            "direccion": "Av Principal",
            "notas": "Cliente VIP",
        }, follow_redirects=False)
        assert resp.status_code == 303
        cli = db.query(models.Cliente).filter_by(nombre="Nuevo Cliente").first()
        assert cli is not None
        assert cli.tipo_documento == "CC"
        assert cli.activo is True

    def test_crear_genera_auditoria(self, admin_client, db):
        admin_client.post("/clientes/nuevo", data={
            "nombre": "Auditado",
            "tipo_documento": "NIT",
            "documento": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "notas": "",
        })
        audit = db.query(models.AuditLog).filter_by(
            accion="CREATE", entidad="cliente"
        ).first()
        assert audit is not None


class TestEditarCliente:
    def test_form_editar(self, admin_client, sample_cliente):
        resp = admin_client.get(f"/clientes/{sample_cliente.id}/editar")
        assert resp.status_code == 200

    def test_editar_ok(self, admin_client, db, sample_cliente):
        resp = admin_client.post(f"/clientes/{sample_cliente.id}/editar", data={
            "nombre": "Cliente Actualizado",
            "tipo_documento": "NIT",
            "documento": "9999999",
            "telefono": "111",
            "email": "upd@test.com",
            "direccion": "Nueva dir",
            "notas": "Nota nueva",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_cliente)
        assert sample_cliente.nombre == "Cliente Actualizado"
        assert sample_cliente.tipo_documento == "NIT"

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.get("/clientes/9999/editar", follow_redirects=False)
        assert resp.status_code == 303

    def test_post_editar_inexistente(self, admin_client):
        """Cubre linea 127: POST editar cliente que no existe."""
        resp = admin_client.post("/clientes/9999/editar", data={
            "nombre": "No Existe",
            "tipo_documento": "CC",
            "documento": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestDetalleCliente:
    def test_detalle_ok(self, admin_client, sample_cliente):
        resp = admin_client.get(f"/clientes/{sample_cliente.id}/detalle")
        assert resp.status_code == 200
        assert "Cliente Test" in resp.text

    def test_detalle_inexistente(self, admin_client):
        resp = admin_client.get("/clientes/9999/detalle", follow_redirects=False)
        assert resp.status_code == 303


class TestEliminarCliente:
    def test_eliminar_soft_delete(self, admin_client, db, sample_cliente):
        resp = admin_client.post(
            f"/clientes/{sample_cliente.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_cliente)
        assert sample_cliente.activo is False

    def test_eliminar_inexistente(self, admin_client):
        """Cubre linea 176: POST eliminar cliente que no existe."""
        resp = admin_client.post(
            "/clientes/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()
