"""Tests para el modulo de auditoria (log de acciones, solo ADMIN)."""
from datetime import datetime
import models
import pytest


class TestAccesoAuditoria:
    def test_admin_puede_acceder(self, admin_client):
        resp = admin_client.get("/auditoria")
        assert resp.status_code == 200

    def test_vendedor_no_puede_acceder(self, vendedor_client):
        resp = vendedor_client.get("/auditoria", follow_redirects=False)
        assert resp.status_code in (303, 403)

    def test_bodeguero_no_puede_acceder(self, bodeguero_client):
        resp = bodeguero_client.get("/auditoria", follow_redirects=False)
        assert resp.status_code in (303, 403)


class TestListaAuditoria:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/auditoria")
        assert resp.status_code == 200

    def test_lista_con_registros(self, admin_client, db, admin_user, sample_local):
        """Crear un registro de auditoria y verificar que aparece."""
        log = models.AuditLog(
            usuario_id=admin_user.id,
            usuario_nombre=admin_user.nombre_completo,
            accion="CREATE",
            entidad="producto",
            entidad_id=1,
            detalle="Producto creado: Test Product",
            ip_address="127.0.0.1",
            created_at=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(log)
        db.commit()

        resp = admin_client.get("/auditoria")
        assert resp.status_code == 200
        assert "Test Product" in resp.text

    def test_filtro_accion(self, admin_client, db, admin_user, sample_local):
        log = models.AuditLog(
            usuario_id=admin_user.id,
            usuario_nombre="Admin Test",
            accion="DELETE",
            entidad="categoria",
            entidad_id=5,
            detalle="Categoria eliminada",
            ip_address="127.0.0.1",
            created_at=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(log)
        db.commit()

        resp = admin_client.get("/auditoria?accion=DELETE")
        assert resp.status_code == 200
        assert "Categoria eliminada" in resp.text

    def test_filtro_entidad(self, admin_client, db, admin_user, sample_local):
        log = models.AuditLog(
            usuario_id=admin_user.id,
            usuario_nombre="Admin Test",
            accion="UPDATE",
            entidad="proveedor",
            entidad_id=3,
            detalle="Proveedor actualizado",
            ip_address="127.0.0.1",
            created_at=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(log)
        db.commit()

        resp = admin_client.get("/auditoria?entidad=proveedor")
        assert resp.status_code == 200
        assert "Proveedor actualizado" in resp.text

    def test_filtro_busqueda(self, admin_client, db, admin_user, sample_local):
        log = models.AuditLog(
            usuario_id=admin_user.id,
            usuario_nombre="Admin Test",
            accion="CREATE",
            entidad="gasto",
            entidad_id=1,
            detalle="Gasto especial registrado",
            ip_address="192.168.1.100",
            created_at=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(log)
        db.commit()

        resp = admin_client.get("/auditoria?buscar=especial")
        assert resp.status_code == 200
        assert "Gasto especial" in resp.text

    def test_filtro_fechas(self, admin_client, db, admin_user, sample_local):
        today = datetime.now().strftime("%Y-%m-%d")
        log = models.AuditLog(
            usuario_id=admin_user.id,
            usuario_nombre="Admin Test",
            accion="CREATE",
            entidad="venta",
            entidad_id=1,
            detalle="Venta de hoy",
            ip_address="127.0.0.1",
            created_at=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(log)
        db.commit()

        resp = admin_client.get(f"/auditoria?fecha_desde={today}&fecha_hasta={today}")
        assert resp.status_code == 200
        assert "Venta de hoy" in resp.text

    def test_filtro_usuario_id(self, admin_client, db, admin_user, sample_local):
        log = models.AuditLog(
            usuario_id=admin_user.id,
            usuario_nombre="Admin Test",
            accion="LOGIN",
            entidad="sesion",
            detalle="Inicio de sesion",
            ip_address="127.0.0.1",
            created_at=datetime.now(),
            local_id=sample_local.id,
        )
        db.add(log)
        db.commit()

        resp = admin_client.get(f"/auditoria?usuario_id={admin_user.id}")
        assert resp.status_code == 200
        assert "Inicio de sesion" in resp.text


class TestAuditoriaFiltrosEdgeCases:
    def test_filtro_fecha_invalida_no_falla(self, admin_client):
        """Cubre linea 43: ValueError en parseo de fecha_desde/fecha_hasta."""
        resp = admin_client.get("/auditoria?fecha_desde=no-valida&fecha_hasta=tampoco")
        assert resp.status_code == 200

    def test_filtro_usuario_id_no_numerico(self, admin_client):
        """Cubre linea 50: ValueError cuando usuario_id no es un entero valido."""
        resp = admin_client.get("/auditoria?usuario_id=abc")
        assert resp.status_code == 200


class TestAuditoriaViaOperaciones:
    def test_crear_acreedor_genera_log(self, admin_client, db):
        """Verificar que operaciones reales generan registros de auditoria."""
        admin_client.post("/acreedores/nuevo", data={
            "nombre": "Acreedor Audit",
            "tipo": "BANCO",
            "documento": "",
            "telefono": "",
            "email": "",
            "direccion": "",
            "notas": "",
        }, follow_redirects=False)

        log = db.query(models.AuditLog).filter(
            models.AuditLog.accion == "CREATE",
            models.AuditLog.entidad == "acreedor",
        ).first()
        assert log is not None
        assert "Acreedor Audit" in log.detalle
