"""Tests para el modulo de configuracion del negocio."""
import models


class TestConfiguracionForm:
    def test_form_admin(self, admin_client, sample_config):
        resp = admin_client.get("/configuracion")
        assert resp.status_code == 200
        assert "Test Store" in resp.text

    def test_form_crea_config_si_no_existe(self, admin_client, db):
        resp = admin_client.get("/configuracion")
        assert resp.status_code == 200
        config = db.query(models.Configuracion).first()
        assert config is not None

    def test_vendedor_no_tiene_acceso(self, vendedor_client):
        resp = vendedor_client.get("/configuracion", follow_redirects=False)
        assert resp.status_code in (303, 403)


class TestGuardarConfiguracion:
    def test_guardar_ok(self, admin_client, db, sample_config):
        resp = admin_client.post("/configuracion", data={
            "nombre_negocio": "Mi Tienda",
            "nit": "900111222",
            "direccion": "Calle 1 #2-3",
            "telefono": "3001112222",
            "email": "tienda@test.com",
            "moneda_simbolo": "$",
            "moneda_codigo": "COP",
            "mensaje_recibo": "Gracias",
            "pie_factura": "Condiciones",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_config)
        assert sample_config.nombre_negocio == "Mi Tienda"
        assert sample_config.nit == "900111222"

    def test_guardar_genera_auditoria(self, admin_client, db, sample_config):
        admin_client.post("/configuracion", data={
            "nombre_negocio": "Auditada",
            "nit": "",
            "direccion": "",
            "telefono": "",
            "email": "",
            "moneda_simbolo": "$",
            "moneda_codigo": "USD",
            "mensaje_recibo": "",
            "pie_factura": "",
        })
        audit = db.query(models.AuditLog).filter_by(
            accion="UPDATE", entidad="configuracion"
        ).first()
        assert audit is not None

    def test_vendedor_no_puede_guardar(self, vendedor_client):
        resp = vendedor_client.post("/configuracion", data={
            "nombre_negocio": "Hack",
            "nit": "",
            "direccion": "",
            "telefono": "",
            "email": "",
            "moneda_simbolo": "$",
            "moneda_codigo": "COP",
            "mensaje_recibo": "",
            "pie_factura": "",
        }, follow_redirects=False)
        assert resp.status_code in (303, 403)
