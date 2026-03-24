"""Tests para el modulo de caja registradora (abrir, cerrar, movimientos, historial)."""
import models


class TestEstadoCaja:
    def test_estado_sin_caja(self, admin_client):
        resp = admin_client.get("/caja")
        assert resp.status_code == 200

    def test_estado_con_caja_abierta(self, admin_client, caja_abierta):
        resp = admin_client.get("/caja")
        assert resp.status_code == 200


class TestAbrirCaja:
    def test_form_abrir(self, admin_client):
        resp = admin_client.get("/caja/abrir")
        assert resp.status_code == 200

    def test_abrir_ok(self, admin_client, db):
        resp = admin_client.post("/caja/abrir", data={
            "monto_apertura": "100000",
        }, follow_redirects=False)
        assert resp.status_code == 303
        caja = db.query(models.Caja).first()
        assert caja is not None
        assert caja.monto_apertura == 100000.0
        assert caja.estado == "ABIERTA"

    def test_abrir_ya_existe(self, admin_client, caja_abierta):
        resp = admin_client.post("/caja/abrir", data={
            "monto_apertura": "50000",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_form_abrir_redirige_si_ya_hay_caja(self, admin_client, caja_abierta):
        resp = admin_client.get("/caja/abrir", follow_redirects=False)
        assert resp.status_code == 303


class TestCerrarCaja:
    def test_cerrar_ok(self, admin_client, db, caja_abierta):
        resp = admin_client.post("/caja/cerrar", data={
            "monto_cierre_real": "100000",
            "notas_cierre": "Sin novedades",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(caja_abierta)
        assert caja_abierta.estado == "CERRADA"
        assert caja_abierta.monto_cierre_real == 100000.0

    def test_cerrar_con_diferencia(self, admin_client, db, caja_abierta):
        admin_client.post("/caja/cerrar", data={
            "monto_cierre_real": "95000",
            "notas_cierre": "Faltante",
        })
        db.refresh(caja_abierta)
        assert caja_abierta.diferencia < 0  # Faltante

    def test_cerrar_sin_caja_abierta(self, admin_client):
        resp = admin_client.post("/caja/cerrar", data={
            "monto_cierre_real": "0",
            "notas_cierre": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_form_cerrar_sin_caja(self, admin_client):
        resp = admin_client.get("/caja/cerrar", follow_redirects=False)
        assert resp.status_code == 303


class TestMovimientoCaja:
    def test_ingreso_manual(self, admin_client, db, caja_abierta):
        resp = admin_client.post("/caja/movimiento", data={
            "tipo": "INGRESO",
            "concepto": "Ingreso prueba",
            "monto": "50000",
        }, follow_redirects=False)
        assert resp.status_code == 303
        mov = db.query(models.MovimientoCaja).filter_by(
            caja_id=caja_abierta.id, tipo="INGRESO"
        ).first()
        assert mov is not None
        assert mov.monto == 50000.0

    def test_egreso_manual(self, admin_client, db, caja_abierta):
        resp = admin_client.post("/caja/movimiento", data={
            "tipo": "EGRESO",
            "concepto": "Gasto prueba",
            "monto": "10000",
        }, follow_redirects=False)
        assert resp.status_code == 303
        mov = db.query(models.MovimientoCaja).filter_by(tipo="EGRESO").first()
        assert mov is not None

    def test_movimiento_monto_cero(self, admin_client, caja_abierta):
        resp = admin_client.post("/caja/movimiento", data={
            "tipo": "INGRESO",
            "concepto": "Invalido",
            "monto": "0",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_movimiento_sin_caja_abierta(self, admin_client):
        resp = admin_client.post("/caja/movimiento", data={
            "tipo": "INGRESO",
            "concepto": "Test",
            "monto": "1000",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestHistorialCajas:
    def test_historial_vacio(self, admin_client):
        resp = admin_client.get("/caja/historial")
        assert resp.status_code == 200

    def test_historial_con_datos(self, admin_client, caja_abierta):
        resp = admin_client.get("/caja/historial")
        assert resp.status_code == 200


class TestDetalleCaja:
    def test_detalle_ok(self, admin_client, caja_abierta):
        resp = admin_client.get(f"/caja/{caja_abierta.id}/detalle")
        assert resp.status_code == 200

    def test_detalle_inexistente(self, admin_client):
        resp = admin_client.get("/caja/9999/detalle", follow_redirects=False)
        assert resp.status_code == 303


class TestModeloCaja:
    def test_saldo_esperado(self, db, caja_abierta):
        mov1 = models.MovimientoCaja(
            caja_id=caja_abierta.id, tipo="INGRESO",
            concepto="Venta", monto=50000.0,
        )
        mov2 = models.MovimientoCaja(
            caja_id=caja_abierta.id, tipo="EGRESO",
            concepto="Gasto", monto=10000.0,
        )
        db.add_all([mov1, mov2])
        db.commit()
        db.refresh(caja_abierta)
        assert caja_abierta.total_ingresos == 50000.0
        assert caja_abierta.total_egresos == 10000.0
        assert caja_abierta.saldo_esperado == 140000.0  # 100000 + 50000 - 10000
