"""Tests para el modulo de gastos del negocio."""
import models


class TestListaGastos:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/gastos")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_gasto):
        resp = admin_client.get("/gastos")
        assert resp.status_code == 200
        assert "Arriendo local" in resp.text

    def test_filtro_tipo(self, admin_client, sample_gasto):
        resp = admin_client.get("/gastos?tipo=DIRECTO")
        assert resp.status_code == 200

    def test_buscar_gasto(self, admin_client, sample_gasto):
        resp = admin_client.get("/gastos?buscar=Arriendo")
        assert resp.status_code == 200


class TestCrearGasto:
    def test_form_nuevo(self, admin_client):
        resp = admin_client.get("/gastos/nuevo")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/gastos/nuevo", data={
            "concepto": "Compra suministros",
            "tipo": "DIRECTO",
            "categoria_gasto": "Suministros",
            "monto": "150000",
            "fecha": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "REC-001",
            "notas": "Nota test",
        }, follow_redirects=False)
        assert resp.status_code == 303
        gasto = db.query(models.Gasto).filter_by(concepto="Compra suministros").first()
        assert gasto is not None
        assert gasto.monto == 150000.0
        assert gasto.tipo == "DIRECTO"

    def test_crear_monto_cero(self, admin_client):
        resp = admin_client.post("/gastos/nuevo", data={
            "concepto": "Test",
            "tipo": "DIRECTO",
            "categoria_gasto": "",
            "monto": "0",
            "fecha": "",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEditarGasto:
    def test_form_editar(self, admin_client, sample_gasto):
        resp = admin_client.get(f"/gastos/{sample_gasto.id}/editar")
        assert resp.status_code == 200

    def test_editar_ok(self, admin_client, db, sample_gasto):
        resp = admin_client.post(f"/gastos/{sample_gasto.id}/editar", data={
            "concepto": "Arriendo actualizado",
            "tipo": "INDIRECTO",
            "categoria_gasto": "Arriendo",
            "monto": "2500000",
            "fecha": "2026-03-20",
            "metodo_pago": "TRANSFERENCIA",
            "comprobante": "TRX-100",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_gasto)
        assert sample_gasto.concepto == "Arriendo actualizado"
        assert sample_gasto.monto == 2500000.0

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.get("/gastos/9999/editar", follow_redirects=False)
        assert resp.status_code == 303


class TestEliminarGasto:
    def test_eliminar_ok(self, admin_client, db, sample_gasto):
        resp = admin_client.post(
            f"/gastos/{sample_gasto.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_gasto)
        assert sample_gasto.activo is False

    def test_eliminar_inexistente(self, admin_client):
        resp = admin_client.post(
            "/gastos/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
