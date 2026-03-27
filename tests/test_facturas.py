"""Tests para el modulo de facturas / cuentas por cobrar."""
import models
from datetime import datetime, timedelta


class TestListaFacturas:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/facturas")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_factura):
        resp = admin_client.get("/facturas")
        assert resp.status_code == 200
        assert "FAC-0001" in resp.text

    def test_filtro_estado(self, admin_client, sample_factura):
        resp = admin_client.get("/facturas?estado=PENDIENTE")
        assert resp.status_code == 200

    def test_buscar_factura(self, admin_client, sample_factura):
        resp = admin_client.get("/facturas?buscar=FAC-0001")
        assert resp.status_code == 200


class TestCrearFactura:
    def test_form_nueva(self, admin_client):
        resp = admin_client.get("/facturas/nueva")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/facturas/nueva", data={
            "numero_factura": "FAC-TEST-001",
            "cliente_nombre": "Cliente Factura",
            "cliente_documento": "111222333",
            "cliente_telefono": "300111222",
            "cliente_email": "fac@test.com",
            "concepto": "Venta equipos",
            "monto_total": "500000",
            "fecha_emision": "2026-03-20",
            "fecha_vencimiento": "2026-04-20",
            "notas": "Nota test",
        }, follow_redirects=False)
        assert resp.status_code == 303
        fac = db.query(models.Factura).filter_by(numero_factura="FAC-TEST-001").first()
        assert fac is not None
        assert fac.monto_total == 500000.0

    def test_crear_numero_duplicado(self, admin_client, sample_factura):
        resp = admin_client.post("/facturas/nueva", data={
            "numero_factura": "FAC-0001",
            "cliente_nombre": "Otro",
            "cliente_documento": "",
            "cliente_telefono": "",
            "cliente_email": "",
            "concepto": "Dup",
            "monto_total": "100",
            "fecha_emision": "2026-03-20",
            "fecha_vencimiento": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEditarFactura:
    def test_form_editar(self, admin_client, sample_factura):
        resp = admin_client.get(f"/facturas/{sample_factura.id}/editar")
        assert resp.status_code == 200

    def test_editar_ok(self, admin_client, db, sample_factura):
        resp = admin_client.post(f"/facturas/{sample_factura.id}/editar", data={
            "numero_factura": "FAC-0001",
            "cliente_nombre": "Cliente Actualizado",
            "cliente_documento": "999",
            "cliente_telefono": "555",
            "cliente_email": "upd@test.com",
            "concepto": "Concepto nuevo",
            "monto_total": "1200000",
            "fecha_emision": "2026-03-20",
            "fecha_vencimiento": "2026-06-20",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_factura)
        assert sample_factura.cliente_nombre == "Cliente Actualizado"
        assert sample_factura.monto_total == 1200000.0


class TestDetalleFactura:
    def test_detalle_ok(self, admin_client, sample_factura):
        resp = admin_client.get(f"/facturas/{sample_factura.id}/detalle")
        assert resp.status_code == 200

    def test_detalle_inexistente(self, admin_client):
        resp = admin_client.get("/facturas/9999/detalle", follow_redirects=False)
        assert resp.status_code == 303


class TestRegistrarCobro:
    def test_cobro_parcial(self, admin_client, db, sample_factura):
        resp = admin_client.post(f"/facturas/{sample_factura.id}/cobrar", data={
            "monto": "200000",
            "fecha_cobro": "2026-03-20",
            "metodo_pago": "TRANSFERENCIA",
            "comprobante": "TRX-001",
            "notas": "Primer cobro",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_factura)
        assert sample_factura.monto_cobrado == 200000.0
        assert sample_factura.estado == "PARCIAL"

    def test_cobro_completo(self, admin_client, db, sample_factura):
        admin_client.post(f"/facturas/{sample_factura.id}/cobrar", data={
            "monto": "1000000",
            "fecha_cobro": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        })
        db.refresh(sample_factura)
        assert sample_factura.estado == "PAGADO"

    def test_cobro_monto_cero(self, admin_client, sample_factura):
        resp = admin_client.post(f"/facturas/{sample_factura.id}/cobrar", data={
            "monto": "0",
            "fecha_cobro": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarCobro:
    def test_eliminar_cobro_ok(self, admin_client, db, sample_factura):
        admin_client.post(f"/facturas/{sample_factura.id}/cobrar", data={
            "monto": "300000",
            "fecha_cobro": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        })
        cobro = db.query(models.PagoFactura).filter_by(factura_id=sample_factura.id).first()
        assert cobro is not None

        resp = admin_client.post(
            f"/facturas/{sample_factura.id}/cobros/{cobro.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_factura)
        assert sample_factura.monto_cobrado == 0.0


class TestEliminarFactura:
    def test_eliminar_ok(self, admin_client, db, sample_factura):
        resp = admin_client.post(
            f"/facturas/{sample_factura.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_factura)
        assert sample_factura.estado == "ANULADO"


class TestReporteFacturas:
    def test_reporte_html(self, admin_client, sample_factura):
        resp = admin_client.get("/facturas/reporte")
        assert resp.status_code == 200


class TestModeloFactura:
    def test_monto_pendiente(self, sample_factura):
        assert sample_factura.monto_pendiente == 1000000.0

    def test_porcentaje_cobrado(self, db, sample_factura):
        sample_factura.monto_cobrado = 500000.0
        db.commit()
        assert sample_factura.porcentaje_cobrado == 50.0

    def test_esta_vencida(self, db, sample_factura):
        sample_factura.fecha_vencimiento = datetime.now() - timedelta(days=1)
        db.commit()
        assert sample_factura.esta_vencida is True
