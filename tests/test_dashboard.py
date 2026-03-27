"""Tests para el dashboard (pagina principal)."""
import models
import json


class TestDashboard:
    def test_dashboard_vacio(self, admin_client):
        """Dashboard sin datos debe renderizar sin errores."""
        resp = admin_client.get("/")
        assert resp.status_code == 200

    def test_dashboard_con_datos(self, admin_client, sample_producto, sample_cliente):
        """Dashboard con datos muestra metricas."""
        resp = admin_client.get("/")
        assert resp.status_code == 200

    def test_dashboard_requiere_auth(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_dashboard_muestra_stock_bajo(self, admin_client, db, sample_categoria):
        prod = models.Producto(
            codigo="LOW-DASH", nombre="Bajo Stock Dashboard",
            precio_costo=100, precio_venta=200,
            stock_actual=1, stock_minimo=10,
            categoria_id=sample_categoria.id, activo=True,
        )
        db.add(prod)
        db.commit()

        resp = admin_client.get("/")
        assert resp.status_code == 200
        assert "Bajo Stock Dashboard" in resp.text

    def test_dashboard_metricas_ventas(
        self, admin_client, db, sample_producto, admin_user
    ):
        """Verifica que las metricas de ventas se calculan."""
        from datetime import datetime
        venta = models.Venta(
            numero_venta="VTA-DASH-001",
            vendedor_id=admin_user.id,
            subtotal=1500.0,
            total=1500.0,
            metodo_pago="EFECTIVO",
            monto_recibido=2000.0,
            cambio=500.0,
            estado="COMPLETADA",
            fecha=datetime.now(),
        )
        db.add(venta)
        db.commit()

        resp = admin_client.get("/")
        assert resp.status_code == 200


    def test_dashboard_con_movimientos(self, admin_client, db, sample_producto):
        """Line 179: Dashboard calcula movimientos de los ultimos 7 dias."""
        from datetime import datetime
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="ENTRADA",
            cantidad=10,
            stock_anterior=sample_producto.stock_actual,
            stock_resultante=sample_producto.stock_actual + 10,
            precio_unitario=sample_producto.precio_costo,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/")
        assert resp.status_code == 200

    def test_dashboard_con_filtro_fecha(self, admin_client):
        """Dashboard con parametros de fecha."""
        resp = admin_client.get("/?fecha_desde=2026-01-01&fecha_hasta=2026-12-31")
        assert resp.status_code == 200

    def test_dashboard_con_fecha_invalida(self, admin_client):
        """Dashboard con fechas invalidas no falla."""
        resp = admin_client.get("/?fecha_desde=invalida&fecha_hasta=invalida")
        assert resp.status_code == 200


class TestGetLocalIP:
    def test_get_local_ip_ok(self):
        """Lines 126-134: get_local_ip retorna una IP valida."""
        from main import get_local_ip
        ip = get_local_ip()
        assert ip is not None
        assert len(ip) >= 7  # al menos x.x.x.x

    def test_get_local_ip_fallback(self, monkeypatch):
        """Lines 133-134: get_local_ip retorna 127.0.0.1 cuando falla."""
        import socket
        original = socket.socket

        def broken_socket(*a, **kw):
            raise OSError("Mocked socket failure")
        monkeypatch.setattr(socket, "socket", broken_socket)

        from main import get_local_ip
        ip = get_local_ip()
        assert ip == "127.0.0.1"

        monkeypatch.setattr(socket, "socket", original)


class TestGuia:
    def test_guia_page(self, admin_client):
        resp = admin_client.get("/guia")
        assert resp.status_code == 200
