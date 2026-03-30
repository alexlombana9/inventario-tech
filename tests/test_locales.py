"""Tests para el modulo de locales (CRUD) y super_dashboard."""
import pytest
from auth import encode_selected_local, decode_selected_local, COOKIE_NAME


# ── Helpers ──────────────────────────────────────────────────


def _second_local(db):
    import models
    local = models.Local(nombre="Sucursal Norte", codigo="SUC-001", activo=True)
    db.add(local)
    db.commit()
    db.refresh(local)
    return local


# ── Acceso SUPERADMIN ────────────────────────────────────────


class TestListaLocales:
    def test_lista_locales_superadmin(self, superadmin_client, sample_local):
        r = superadmin_client.get("/locales", follow_redirects=False)
        assert r.status_code == 200
        assert b"Local Test" in r.content

    def test_lista_locales_admin_forbidden(self, admin_client):
        r = admin_client.get("/locales", follow_redirects=False)
        assert r.status_code in (403, 303)

    def test_lista_locales_buscar(self, superadmin_client, sample_local, db):
        _second_local(db)
        r = superadmin_client.get("/locales?q=Sucursal", follow_redirects=False)
        assert r.status_code == 200
        assert b"Sucursal Norte" in r.content


class TestCrearLocal:
    def test_form_nuevo_local(self, superadmin_client):
        r = superadmin_client.get("/locales/nuevo", follow_redirects=False)
        assert r.status_code == 200

    def test_crear_local_ok(self, superadmin_client, db):
        r = superadmin_client.post("/locales/nuevo", data={
            "nombre": "Nuevo Local",
            "codigo": "NL-001",
            "direccion": "Calle 123",
            "telefono": "3001234567",
            "email": "nuevo@test.com",
            "ciudad": "Bogota",
            "responsable": "Juan",
        }, follow_redirects=False)
        assert r.status_code == 303
        assert "/locales" in r.headers["location"]

        import models
        local = db.query(models.Local).filter(models.Local.codigo == "NL-001").first()
        assert local is not None
        assert local.nombre == "Nuevo Local"
        # Verifica que se creo configuracion
        config = db.query(models.Configuracion).filter(models.Configuracion.local_id == local.id).first()
        assert config is not None

    def test_crear_local_codigo_duplicado(self, superadmin_client, sample_local):
        r = superadmin_client.post("/locales/nuevo", data={
            "nombre": "Duplicado",
            "codigo": "TEST-001",
        }, follow_redirects=False)
        assert r.status_code == 303
        assert "error" in r.headers["location"].lower() or "nuevo" in r.headers["location"]


class TestEditarLocal:
    def test_form_editar_local(self, superadmin_client, sample_local):
        r = superadmin_client.get(f"/locales/{sample_local.id}/editar", follow_redirects=False)
        assert r.status_code == 200

    def test_editar_local_ok(self, superadmin_client, sample_local, db):
        r = superadmin_client.post(f"/locales/{sample_local.id}/editar", data={
            "nombre": "Local Editado",
            "codigo": "TEST-001",
            "direccion": "Nueva dir",
            "telefono": "",
            "email": "",
            "ciudad": "",
            "responsable": "",
        }, follow_redirects=False)
        assert r.status_code == 303
        db.refresh(sample_local)
        assert sample_local.nombre == "Local Editado"

    def test_editar_local_no_existe(self, superadmin_client):
        r = superadmin_client.get("/locales/9999/editar", follow_redirects=False)
        assert r.status_code == 303

    def test_editar_local_codigo_duplicado(self, superadmin_client, sample_local, db):
        local2 = _second_local(db)
        r = superadmin_client.post(f"/locales/{sample_local.id}/editar", data={
            "nombre": "Local Test",
            "codigo": "SUC-001",  # codigo de local2
        }, follow_redirects=False)
        assert r.status_code == 303
        assert "error" in r.headers["location"].lower() or "editar" in r.headers["location"]


class TestToggleLocal:
    def test_toggle_local(self, superadmin_client, sample_local, db):
        assert sample_local.activo is True
        r = superadmin_client.post(f"/locales/{sample_local.id}/toggle", follow_redirects=False)
        assert r.status_code == 303
        db.refresh(sample_local)
        assert sample_local.activo is False

        # Toggle de vuelta
        r = superadmin_client.post(f"/locales/{sample_local.id}/toggle", follow_redirects=False)
        assert r.status_code == 303
        db.refresh(sample_local)
        assert sample_local.activo is True

    def test_toggle_local_no_existe(self, superadmin_client):
        r = superadmin_client.post("/locales/9999/toggle", follow_redirects=False)
        assert r.status_code == 303


class TestSeleccionarLocal:
    def test_seleccionar_local(self, superadmin_client, sample_local):
        r = superadmin_client.get(f"/locales/seleccionar/{sample_local.id}", follow_redirects=False)
        assert r.status_code == 303
        assert "/" == r.headers["location"] or r.headers["location"] == "/"
        # Verifica que la cookie esta seteada y es firmada (no un int plano)
        cookie = superadmin_client.cookies.get("techstock_selected_local")
        assert cookie is not None
        decoded = decode_selected_local(cookie)
        assert decoded == sample_local.id

    def test_seleccionar_local_no_existe(self, superadmin_client):
        r = superadmin_client.get("/locales/seleccionar/9999", follow_redirects=False)
        assert r.status_code == 303
        assert "error" in r.headers["location"].lower() or "locales" in r.headers["location"]

    def test_deseleccionar_local(self, superadmin_client, sample_local):
        # Primero seleccionar
        superadmin_client.get(f"/locales/seleccionar/{sample_local.id}", follow_redirects=False)
        # Luego deseleccionar
        r = superadmin_client.get("/locales/deseleccionar", follow_redirects=False)
        assert r.status_code == 303
        assert "/super" in r.headers["location"]


# ── Cookie firmada ───────────────────────────────────────────


class TestCookieFirmada:
    def test_encode_decode(self):
        encoded = encode_selected_local(42)
        assert isinstance(encoded, str)
        assert decode_selected_local(encoded) == 42

    def test_decode_tampered(self):
        assert decode_selected_local("tampered_value") is None

    def test_decode_empty(self):
        assert decode_selected_local("") is None
        assert decode_selected_local(None) is None

    def test_decode_plain_int(self):
        """Un int plano (cookie sin firmar) debe ser rechazado."""
        assert decode_selected_local("5") is None


# ── Super Dashboard ──────────────────────────────────────────


class TestSuperDashboard:
    def test_super_dashboard_acceso(self, superadmin_client, sample_local):
        r = superadmin_client.get("/super", follow_redirects=False)
        assert r.status_code == 200
        assert b"Dashboard General" in r.content

    def test_super_dashboard_admin_forbidden(self, admin_client):
        r = admin_client.get("/super", follow_redirects=False)
        assert r.status_code in (403, 303)

    def test_super_dashboard_muestra_locales(self, superadmin_client, sample_local, db):
        _second_local(db)
        r = superadmin_client.get("/super", follow_redirects=False)
        assert r.status_code == 200
        assert b"Local Test" in r.content
        assert b"Sucursal Norte" in r.content

    def test_super_dashboard_con_ventas(self, superadmin_client, superadmin_user, sample_local, db):
        """Dashboard funciona aunque haya ventas."""
        import models
        from datetime import datetime
        venta = models.Venta(
            numero_venta="VTA-0001",
            cliente_nombre="Test",
            vendedor_id=superadmin_user.id,
            subtotal=50000,
            total=50000,
            metodo_pago="EFECTIVO",
            estado="COMPLETADA",
            fecha=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(venta)
        db.commit()
        r = superadmin_client.get("/super", follow_redirects=False)
        assert r.status_code == 200
