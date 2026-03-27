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

    def test_filtro_fecha_desde_valida(self, admin_client, sample_gasto):
        """Lines 46, 52: fecha_desde valida es parseada y aplica filtro."""
        resp = admin_client.get("/gastos?fecha_desde=2026-01-01&fecha_hasta=2026-12-31")
        assert resp.status_code == 200

    def test_filtro_fecha_solo_desde(self, admin_client, sample_gasto):
        """Line 46: Solo fecha_desde proporcionada, fecha_hasta usa default."""
        resp = admin_client.get("/gastos?fecha_desde=2026-01-01")
        assert resp.status_code == 200

    def test_filtro_categoria_gasto(self, admin_client, sample_gasto):
        """Line 52: filtro por categoria_gasto."""
        resp = admin_client.get("/gastos?categoria_gasto=Arriendo")
        assert resp.status_code == 200

    def test_filtro_fecha_invalida(self, admin_client, sample_gasto):
        """Line 46: except ValueError cuando las fechas son invalidas."""
        resp = admin_client.get("/gastos?fecha_desde=no-fecha&fecha_hasta=tampoco")
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

    def test_crear_con_fecha_invalida(self, admin_client, db):
        """Line 147: fecha invalida usa datetime.now() como fallback."""
        resp = admin_client.post("/gastos/nuevo", data={
            "concepto": "Fecha mala",
            "tipo": "DIRECTO",
            "categoria_gasto": "Otros",
            "monto": "5000",
            "fecha": "no-es-fecha",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        gasto = db.query(models.Gasto).filter_by(concepto="Fecha mala").first()
        assert gasto is not None

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

    def test_editar_post_monto_invalido(self, admin_client, sample_gasto):
        """Lines 137-138: Monto no numerico redirige con error."""
        resp = admin_client.post(f"/gastos/{sample_gasto.id}/editar", data={
            "concepto": "Test",
            "tipo": "DIRECTO",
            "categoria_gasto": "",
            "monto": "no_es_numero",
            "fecha": "",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_editar_post_inexistente(self, admin_client):
        """Line 213: POST editar gasto inexistente redirige con error."""
        resp = admin_client.post("/gastos/9999/editar", data={
            "concepto": "Nadie",
            "tipo": "DIRECTO",
            "categoria_gasto": "",
            "monto": "100",
            "fecha": "",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_editar_con_fecha_invalida(self, admin_client, db, sample_gasto):
        """Line 231: fecha invalida no modifica la fecha original."""
        fecha_original = sample_gasto.fecha
        resp = admin_client.post(f"/gastos/{sample_gasto.id}/editar", data={
            "concepto": "Fecha invalida edit",
            "tipo": "DIRECTO",
            "categoria_gasto": "Arriendo",
            "monto": "1000000",
            "fecha": "no-es-fecha",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_gasto)
        assert sample_gasto.fecha == fecha_original

    def test_editar_sin_fecha(self, admin_client, db, sample_gasto):
        """Line 147: fecha vacia no modifica la fecha del gasto."""
        fecha_original = sample_gasto.fecha
        resp = admin_client.post(f"/gastos/{sample_gasto.id}/editar", data={
            "concepto": "Sin fecha",
            "tipo": "DIRECTO",
            "categoria_gasto": "Arriendo",
            "monto": "1000000",
            "fecha": "",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_gasto)
        assert sample_gasto.fecha == fecha_original


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

    def test_eliminar_genera_auditoria(self, admin_client, db, sample_gasto):
        """Lines 217-218: Eliminar registra entrada en audit log."""
        admin_client.post(
            f"/gastos/{sample_gasto.id}/eliminar",
            follow_redirects=False,
        )
        log = db.query(models.AuditLog).filter_by(
            accion="DELETE", entidad="gasto"
        ).first()
        assert log is not None

    def test_eliminar_ya_inactivo_retorna_error(self, admin_client, db, sample_gasto):
        """Line 231: Intentar eliminar gasto ya eliminado redirige con error."""
        # Primero desactivar directamente en DB
        sample_gasto.activo = False
        db.commit()

        resp = admin_client.post(
            f"/gastos/{sample_gasto.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_crear_monto_invalido(self, admin_client):
        """Lines 137-138 crear: monto no numerico redirige con error."""
        resp = admin_client.post("/gastos/nuevo", data={
            "concepto": "Test invalido",
            "tipo": "DIRECTO",
            "categoria_gasto": "",
            "monto": "abc",
            "fecha": "",
            "metodo_pago": "EFECTIVO",
            "comprobante": "",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()
