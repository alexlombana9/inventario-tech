"""Tests para el modulo de deudas / cuentas por pagar."""
import models
from datetime import datetime, timedelta


class TestListaDeudas:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/deudas")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_deuda):
        resp = admin_client.get("/deudas")
        assert resp.status_code == 200
        assert "Compra de mercancia" in resp.text

    def test_filtro_estado(self, admin_client, sample_deuda):
        resp = admin_client.get("/deudas?estado=PENDIENTE")
        assert resp.status_code == 200

    def test_filtro_acreedor_tipo(self, admin_client, sample_deuda):
        resp = admin_client.get("/deudas?acreedor_tipo=PROVEEDOR")
        assert resp.status_code == 200

    def test_buscar_acreedor(self, admin_client, sample_deuda):
        resp = admin_client.get("/deudas?buscar=Proveedor")
        assert resp.status_code == 200


class TestCrearDeuda:
    def test_form_nueva(self, admin_client, sample_proveedor):
        resp = admin_client.get("/deudas/nueva")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db, sample_proveedor):
        resp = admin_client.post("/deudas/nueva", data={
            "concepto": "Compra equipos",
            "acreedor_nombre": sample_proveedor.nombre,
            "acreedor_tipo": "PROVEEDOR",
            "proveedor_id": str(sample_proveedor.id),
            "monto_total": "250000",
            "fecha_deuda": "2026-03-20",
            "fecha_vencimiento": "2026-04-20",
            "notas": "Pagar antes del 20",
        }, follow_redirects=False)
        assert resp.status_code == 303
        deuda = db.query(models.Deuda).filter_by(concepto="Compra equipos").first()
        assert deuda is not None
        assert deuda.monto_total == 250000.0
        assert deuda.estado == "PENDIENTE"


class TestEditarDeuda:
    def test_form_editar(self, admin_client, sample_deuda):
        resp = admin_client.get(f"/deudas/{sample_deuda.id}/editar")
        assert resp.status_code == 200

    def test_editar_ok(self, admin_client, db, sample_deuda):
        resp = admin_client.post(f"/deudas/{sample_deuda.id}/editar", data={
            "concepto": "Concepto actualizado",
            "acreedor_nombre": sample_deuda.acreedor_nombre,
            "acreedor_tipo": "PROVEEDOR",
            "proveedor_id": str(sample_deuda.proveedor_id),
            "monto_total": "600000",
            "fecha_deuda": "2026-03-20",
            "fecha_vencimiento": "2026-05-20",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_deuda)
        assert sample_deuda.concepto == "Concepto actualizado"
        assert sample_deuda.monto_total == 600000.0

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.get("/deudas/9999/editar", follow_redirects=False)
        assert resp.status_code == 303


class TestDetalleDeuda:
    def test_detalle_ok(self, admin_client, sample_deuda):
        resp = admin_client.get(f"/deudas/{sample_deuda.id}/detalle")
        assert resp.status_code == 200

    def test_detalle_inexistente(self, admin_client):
        resp = admin_client.get("/deudas/9999/detalle", follow_redirects=False)
        assert resp.status_code == 303


class TestRegistrarPago:
    def test_pago_parcial(self, admin_client, db, sample_deuda):
        resp = admin_client.post(f"/deudas/{sample_deuda.id}/pagar", data={
            "monto": "100000",
            "fecha_pago": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "REC-001",
            "notas": "Primer abono",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_deuda)
        assert sample_deuda.monto_pagado == 100000.0
        assert sample_deuda.estado == "PARCIAL"

    def test_pago_completo(self, admin_client, db, sample_deuda):
        admin_client.post(f"/deudas/{sample_deuda.id}/pagar", data={
            "monto": "500000",
            "fecha_pago": "2026-03-20",
            "metodo_pago": "TRANSFERENCIA",
            "comprobante": "",
            "notas": "",
        })
        db.refresh(sample_deuda)
        assert sample_deuda.estado == "PAGADO"
        assert sample_deuda.monto_pendiente == 0.0

    def test_pago_excede_monto(self, admin_client, db, sample_deuda):
        """El pago se limita al monto pendiente."""
        admin_client.post(f"/deudas/{sample_deuda.id}/pagar", data={
            "monto": "999999",
            "fecha_pago": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        })
        db.refresh(sample_deuda)
        assert sample_deuda.monto_pagado == 500000.0  # Limitado al total
        assert sample_deuda.estado == "PAGADO"

    def test_pago_monto_cero(self, admin_client, sample_deuda):
        resp = admin_client.post(f"/deudas/{sample_deuda.id}/pagar", data={
            "monto": "0",
            "fecha_pago": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_pago_deuda_ya_pagada(self, admin_client, db, sample_deuda):
        sample_deuda.monto_pagado = sample_deuda.monto_total
        sample_deuda.estado = "PAGADO"
        db.commit()

        resp = admin_client.post(f"/deudas/{sample_deuda.id}/pagar", data={
            "monto": "1000",
            "fecha_pago": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarPago:
    def test_eliminar_pago_ok(self, admin_client, db, sample_deuda):
        # Primero registrar un pago
        admin_client.post(f"/deudas/{sample_deuda.id}/pagar", data={
            "monto": "100000",
            "fecha_pago": "2026-03-20",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        })
        pago = db.query(models.PagoDeuda).filter_by(deuda_id=sample_deuda.id).first()
        assert pago is not None

        resp = admin_client.post(
            f"/deudas/{sample_deuda.id}/pagos/{pago.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_deuda)
        assert sample_deuda.monto_pagado == 0.0
        assert sample_deuda.estado == "PENDIENTE"


class TestEliminarDeuda:
    def test_eliminar_ok(self, admin_client, db, sample_deuda):
        resp = admin_client.post(
            f"/deudas/{sample_deuda.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_deuda)
        assert sample_deuda.estado == "ANULADO"


class TestReporteDeudas:
    def test_reporte_html(self, admin_client, sample_deuda):
        resp = admin_client.get("/deudas/reporte")
        assert resp.status_code == 200


class TestModeloDeuda:
    def test_monto_pendiente(self, sample_deuda):
        assert sample_deuda.monto_pendiente == 500000.0

    def test_porcentaje_pagado(self, db, sample_deuda):
        sample_deuda.monto_pagado = 250000.0
        db.commit()
        assert sample_deuda.porcentaje_pagado == 50.0

    def test_esta_vencida(self, db, sample_deuda):
        sample_deuda.fecha_vencimiento = datetime.now() - timedelta(days=1)
        db.commit()
        assert sample_deuda.esta_vencida is True

    def test_no_vencida_si_pagada(self, db, sample_deuda):
        sample_deuda.estado = "PAGADO"
        sample_deuda.fecha_vencimiento = datetime.now() - timedelta(days=1)
        db.commit()
        assert sample_deuda.esta_vencida is False
