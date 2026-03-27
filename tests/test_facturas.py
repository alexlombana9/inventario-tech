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


class TestListaFacturasFiltrosFecha:
    """Cubre lineas 54-66 — filtros de fecha y vencidas en lista."""

    def test_filtro_fecha_desde(self, admin_client, sample_factura):
        """Lineas 54-58: filtro fecha_desde."""
        resp = admin_client.get("/facturas?fecha_desde=2026-01-01")
        assert resp.status_code == 200

    def test_filtro_fecha_hasta(self, admin_client, sample_factura):
        """Lineas 60-64: filtro fecha_hasta."""
        resp = admin_client.get("/facturas?fecha_hasta=2026-12-31")
        assert resp.status_code == 200

    def test_filtro_fechas_invalidas(self, admin_client, sample_factura):
        """Lineas 57, 63: ValueError en fechas invalidas se ignora."""
        resp = admin_client.get("/facturas?fecha_desde=no-date&fecha_hasta=no-date")
        assert resp.status_code == 200

    def test_filtro_vencidas(self, admin_client, db, sample_factura):
        """Linea 65-69: filtro vencidas=1 muestra solo facturas vencidas."""
        sample_factura.fecha_vencimiento = datetime.now() - timedelta(days=5)
        db.commit()
        resp = admin_client.get("/facturas?vencidas=1")
        assert resp.status_code == 200
        assert "FAC-0001" in resp.text

    def test_filtro_vencidas_no_activo(self, admin_client, sample_factura):
        """Cuando vencidas != '1' no se aplica el filtro."""
        resp = admin_client.get("/facturas?vencidas=0")
        assert resp.status_code == 200


class TestEditarFacturaPostNotFound:
    """Cubre linea 161 (GET) y 190 (POST) — editar factura inexistente."""

    def test_get_editar_inexistente(self, admin_client):
        """GET editar factura inexistente → redirect con error."""
        resp = admin_client.get("/facturas/9999/editar", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_post_editar_inexistente(self, admin_client):
        """Linea 190: POST editar factura inexistente → redirect con error."""
        resp = admin_client.post("/facturas/9999/editar", data={
            "numero_factura": "FAC-NOPE",
            "cliente_nombre": "Test",
            "cliente_documento": "",
            "cliente_telefono": "",
            "cliente_email": "",
            "concepto": "Nada",
            "monto_total": "100",
            "fecha_emision": "2026-01-01",
            "fecha_vencimiento": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_post_editar_numero_duplicado(self, admin_client, db, sample_factura):
        """Linea 197: numero_factura ya en uso por otra factura → redirect con error."""
        # Crear una segunda factura
        from datetime import datetime as dt
        segunda = models.Factura(
            numero_factura="FAC-0002",
            cliente_nombre="Otro Cliente",
            concepto="Otro concepto",
            monto_total=500.0,
            monto_cobrado=0.0,
            fecha_emision=dt.now(),
            estado="PENDIENTE",
        )
        db.add(segunda)
        db.commit()

        # Intentar renombrar sample_factura (FAC-0001) a FAC-0002 (ya en uso)
        resp = admin_client.post(f"/facturas/{sample_factura.id}/editar", data={
            "numero_factura": "FAC-0002",
            "cliente_nombre": "Test",
            "cliente_documento": "",
            "cliente_telefono": "",
            "cliente_email": "",
            "concepto": "Test",
            "monto_total": "1000000",
            "fecha_emision": "2026-01-01",
            "fecha_vencimiento": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestCobroFacturaEdgeCases:
    """Cubre lineas 257, 259 — cobro de factura inexistente y ya pagada."""

    def test_cobro_factura_inexistente(self, admin_client):
        """Linea 257: factura no encontrada → redirect con error."""
        resp = admin_client.post("/facturas/9999/cobrar", data={
            "monto": "1000",
            "fecha_cobro": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_cobro_factura_ya_pagada(self, admin_client, db, sample_factura):
        """Linea 259: factura ya cobrada completamente → redirect con error."""
        sample_factura.monto_cobrado = sample_factura.monto_total
        sample_factura.estado = "PAGADO"
        db.commit()

        resp = admin_client.post(f"/facturas/{sample_factura.id}/cobrar", data={
            "monto": "500",
            "fecha_cobro": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarCobroNotFound:
    """Cubre linea 295 — eliminar cobro inexistente."""

    def test_eliminar_cobro_inexistente(self, admin_client, sample_factura):
        """Linea 295: cobro no encontrado → redirect con error."""
        resp = admin_client.post(
            f"/facturas/{sample_factura.id}/cobros/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestAnularFacturaEdgeCases:
    """Cubre lineas 330, 334 y 432 — anular factura y casos de borde."""

    def test_anular_factura_inexistente(self, admin_client):
        """Linea 432: factura no encontrada en eliminar → redirect con error."""
        resp = admin_client.post("/facturas/9999/eliminar", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestReporteFacturasFiltros:
    """Cubre lineas 330-334 y 366-420 — reporte HTML y PDF con filtros."""

    def test_reporte_con_estado(self, admin_client, sample_factura):
        """Linea 333-334: reporte filtrado por estado."""
        resp = admin_client.get("/facturas/reporte?estado=PENDIENTE")
        assert resp.status_code == 200

    def test_reporte_con_fechas(self, admin_client, sample_factura):
        """Lineas 326-329: reporte con fechas explicitas."""
        resp = admin_client.get("/facturas/reporte?fecha_desde=2026-01-01&fecha_hasta=2026-12-31")
        assert resp.status_code == 200

    def test_reporte_con_factura_vencida(self, admin_client, db, sample_factura):
        """Reporte incluye facturas vencidas (estado_txt = 'VENCIDA')."""
        sample_factura.fecha_vencimiento = datetime.now() - timedelta(days=5)
        db.commit()
        resp = admin_client.get("/facturas/reporte")
        assert resp.status_code == 200

    def test_reporte_pdf_vacio(self, admin_client):
        """PDF con tabla vacia."""
        resp = admin_client.get("/facturas/reporte/pdf?fecha_desde=2000-01-01&fecha_hasta=2000-01-02")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_reporte_pdf_con_datos(self, admin_client, sample_factura):
        """Lineas 366-420: generacion de PDF del reporte de facturas."""
        resp = admin_client.get("/facturas/reporte/pdf")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_reporte_pdf_con_estado(self, admin_client, sample_factura):
        """PDF filtrado por estado."""
        resp = admin_client.get("/facturas/reporte/pdf?estado=PENDIENTE")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_reporte_pdf_con_fechas(self, admin_client, sample_factura):
        """PDF con rango de fechas explicito."""
        resp = admin_client.get("/facturas/reporte/pdf?fecha_desde=2026-01-01&fecha_hasta=2026-12-31")
        assert resp.status_code == 200

    def test_reporte_pdf_factura_vencida(self, admin_client, db, sample_factura):
        """PDF incluye facturas vencidas con estado_txt VENCIDA."""
        sample_factura.fecha_vencimiento = datetime.now() - timedelta(days=3)
        db.commit()
        resp = admin_client.get("/facturas/reporte/pdf")
        assert resp.status_code == 200

    def test_reporte_fecha_invalida(self, admin_client, sample_factura):
        """Linea 330: except ValueError en reporte HTML con fechas invalidas."""
        resp = admin_client.get("/facturas/reporte?fecha_desde=no-date&fecha_hasta=no-date")
        assert resp.status_code == 200

    def test_reporte_pdf_fecha_invalida(self, admin_client, sample_factura):
        """Linea 378: except ValueError en reporte PDF con fechas invalidas."""
        resp = admin_client.get("/facturas/reporte/pdf?fecha_desde=no-date&fecha_hasta=no-date")
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
