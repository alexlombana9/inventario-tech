"""Tests para el modulo de configuracion del negocio."""
import io
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

    def test_guardar_nombre_vacio_usa_default(self, admin_client, db, sample_config):
        """Lines 83-105: nombre_negocio vacio usa 'TechStock' como default."""
        resp = admin_client.post("/configuracion", data={
            "nombre_negocio": "   ",
            "nit": "",
            "direccion": "",
            "telefono": "",
            "email": "",
            "moneda_simbolo": "$",
            "moneda_codigo": "COP",
            "mensaje_recibo": "",
            "pie_factura": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_config)
        assert sample_config.nombre_negocio == "TechStock"

    def test_guardar_simbolo_vacio_usa_default(self, admin_client, db, sample_config):
        """Lines 83-105: moneda_simbolo vacio usa '$' como default."""
        resp = admin_client.post("/configuracion", data={
            "nombre_negocio": "Tienda",
            "nit": "",
            "direccion": "",
            "telefono": "",
            "email": "",
            "moneda_simbolo": "   ",
            "moneda_codigo": "   ",
            "mensaje_recibo": "",
            "pie_factura": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_config)
        assert sample_config.moneda_simbolo == "$"
        assert sample_config.moneda_codigo == "COP"

    def test_guardar_todos_los_campos(self, admin_client, db, sample_config):
        """Lines 83-105: Guarda correctamente todos los campos del formulario."""
        resp = admin_client.post("/configuracion", data={
            "nombre_negocio": "Orionics Tech",
            "nit": "830123456-1",
            "direccion": "Calle 50 #30-10, Barrancabermeja",
            "telefono": "6057654321",
            "email": "contacto@orionics.co",
            "moneda_simbolo": "COP$",
            "moneda_codigo": "COP",
            "mensaje_recibo": "Gracias por su compra en Orionics",
            "pie_factura": "SOMOS RESPONSABLES DE IVA",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_config)
        assert sample_config.nombre_negocio == "Orionics Tech"
        assert sample_config.nit == "830123456-1"
        assert sample_config.direccion == "Calle 50 #30-10, Barrancabermeja"
        assert sample_config.telefono == "6057654321"
        assert sample_config.email == "contacto@orionics.co"
        assert sample_config.mensaje_recibo == "Gracias por su compra en Orionics"
        assert sample_config.pie_factura == "SOMOS RESPONSABLES DE IVA"

    def test_guardar_crea_config_si_no_existe(self, admin_client, db):
        """Lines 83-105: Si no hay config existente, se crea una nueva."""
        resp = admin_client.post("/configuracion", data={
            "nombre_negocio": "Nueva Tienda",
            "nit": "123",
            "direccion": "",
            "telefono": "",
            "email": "",
            "moneda_simbolo": "$",
            "moneda_codigo": "COP",
            "mensaje_recibo": "",
            "pie_factura": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        config = db.query(models.Configuracion).first()
        assert config is not None
        assert config.nombre_negocio == "Nueva Tienda"


class TestSubirLogo:
    def test_logo_sin_archivo(self, admin_client, sample_config):
        """Line 83: logo.filename vacio redirige con error o 422."""
        resp = admin_client.post(
            "/configuracion/logo",
            files={"logo": ("", io.BytesIO(b""), "application/octet-stream")},
            follow_redirects=False,
        )
        # FastAPI may reject empty filename with 422 before reaching app code
        assert resp.status_code in (303, 422)

    def test_logo_extension_invalida(self, admin_client, sample_config):
        """Lines 86-88: Extension no permitida redirige con error."""
        resp = admin_client.post(
            "/configuracion/logo",
            files={"logo": ("logo.bmp", io.BytesIO(b"data"), "image/bmp")},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_logo_muy_grande(self, admin_client, sample_config):
        """Lines 90-92: Imagen mayor a 2MB rechazada."""
        big = b"x" * (2 * 1024 * 1024 + 1)
        resp = admin_client.post(
            "/configuracion/logo",
            files={"logo": ("logo.png", io.BytesIO(big), "image/png")},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_logo_ok(self, admin_client, db, sample_config, tmp_path, monkeypatch):
        """Lines 94-105: Subir logo valido."""
        import routers.configuracion as config_mod
        monkeypatch.setattr(config_mod, "UPLOAD_DIR", str(tmp_path))
        resp = admin_client.post(
            "/configuracion/logo",
            files={"logo": ("logo.png", io.BytesIO(b"\x89PNG\r\n"), "image/png")},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_config)
        assert "logo.png" in sample_config.logo_path
