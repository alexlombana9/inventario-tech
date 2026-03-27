"""Tests para el modulo de acreedores (CRUD)."""
import models


class TestListaAcreedores:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/acreedores")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_acreedor):
        resp = admin_client.get("/acreedores")
        assert resp.status_code == 200
        assert "Acreedor Test" in resp.text

    def test_buscar_acreedor(self, admin_client, sample_acreedor):
        resp = admin_client.get("/acreedores?buscar=Acreedor")
        assert resp.status_code == 200
        assert "Acreedor Test" in resp.text

    def test_buscar_sin_resultados(self, admin_client, sample_acreedor):
        resp = admin_client.get("/acreedores?buscar=Inexistente")
        assert resp.status_code == 200
        assert "Acreedor Test" not in resp.text

    def test_filtro_tipo(self, admin_client, sample_acreedor):
        resp = admin_client.get("/acreedores?tipo=PROVEEDOR")
        assert resp.status_code == 200
        assert "Acreedor Test" in resp.text

    def test_filtro_tipo_sin_resultados(self, admin_client, sample_acreedor):
        resp = admin_client.get("/acreedores?tipo=BANCO")
        assert resp.status_code == 200
        assert "Acreedor Test" not in resp.text


class TestCrearAcreedor:
    def test_form_nuevo(self, admin_client):
        resp = admin_client.get("/acreedores/nuevo")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/acreedores/nuevo", data={
            "nombre": "Banco Nacional",
            "tipo": "BANCO",
            "documento": "800111333",
            "telefono": "6011234567",
            "email": "banco@test.com",
            "direccion": "Calle 123",
            "notas": "Nota de prueba",
        }, follow_redirects=False)
        assert resp.status_code == 303
        acreedor = db.query(models.Acreedor).filter_by(nombre="Banco Nacional").first()
        assert acreedor is not None
        assert acreedor.tipo == "BANCO"
        assert acreedor.documento == "800111333"
        assert acreedor.activo is True

    def test_crear_tipo_default(self, admin_client, db):
        resp = admin_client.post("/acreedores/nuevo", data={
            "nombre": "Persona Natural",
            "documento": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        acreedor = db.query(models.Acreedor).filter_by(nombre="Persona Natural").first()
        assert acreedor is not None
        assert acreedor.tipo == "OTRO"

    def test_crear_genera_auditoria(self, admin_client, db):
        admin_client.post("/acreedores/nuevo", data={
            "nombre": "Auditado",
            "tipo": "PERSONA",
            "documento": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "notas": "",
        }, follow_redirects=False)
        log = db.query(models.AuditLog).filter(
            models.AuditLog.entidad == "acreedor",
            models.AuditLog.accion == "CREATE",
        ).first()
        assert log is not None
        assert "Auditado" in log.detalle


class TestEditarAcreedor:
    def test_form_editar(self, admin_client, sample_acreedor):
        resp = admin_client.get(f"/acreedores/{sample_acreedor.id}/editar")
        assert resp.status_code == 200

    def test_editar_ok(self, admin_client, db, sample_acreedor):
        resp = admin_client.post(f"/acreedores/{sample_acreedor.id}/editar", data={
            "nombre": "Acreedor Actualizado",
            "tipo": "BANCO",
            "documento": "999888777",
            "telefono": "3009998888",
            "email": "nuevo@test.com",
            "direccion": "Av Nueva 456",
            "notas": "Actualizado",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_acreedor)
        assert sample_acreedor.nombre == "Acreedor Actualizado"
        assert sample_acreedor.tipo == "BANCO"
        assert sample_acreedor.documento == "999888777"

    def test_editar_inexistente_form(self, admin_client):
        resp = admin_client.get("/acreedores/9999/editar", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_editar_inexistente_post(self, admin_client):
        resp = admin_client.post("/acreedores/9999/editar", data={
            "nombre": "Nada",
            "tipo": "OTRO",
            "documento": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarAcreedor:
    def test_eliminar_ok(self, admin_client, db, sample_acreedor):
        resp = admin_client.post(
            f"/acreedores/{sample_acreedor.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_acreedor)
        assert sample_acreedor.activo is False

    def test_eliminar_inexistente(self, admin_client):
        resp = admin_client.post(
            "/acreedores/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_eliminar_genera_auditoria(self, admin_client, db, sample_acreedor):
        admin_client.post(
            f"/acreedores/{sample_acreedor.id}/eliminar",
            follow_redirects=False,
        )
        log = db.query(models.AuditLog).filter(
            models.AuditLog.entidad == "acreedor",
            models.AuditLog.accion == "DELETE",
        ).first()
        assert log is not None
