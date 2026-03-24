"""Tests para el modulo de ventas/POS (procesar, historial, anular, recibo)."""
import json
import models


class TestPOSInterface:
    def test_pos_page(self, admin_client, sample_producto):
        resp = admin_client.get("/ventas/pos")
        assert resp.status_code == 200

    def test_api_buscar_productos(self, admin_client, sample_producto):
        resp = admin_client.get("/ventas/api/productos?q=Laptop")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["nombre"] == "Laptop Test"

    def test_api_buscar_sin_resultados(self, admin_client, sample_producto):
        resp = admin_client.get("/ventas/api/productos?q=NoExiste")
        assert resp.status_code == 200
        assert resp.json() == []


class TestProcesarVenta:
    def test_venta_ok(self, admin_client, db, sample_producto, sample_cliente):
        stock_inicial = sample_producto.stock_actual
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 2,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": str(sample_cliente.id),
            "cliente_nombre": sample_cliente.nombre,
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "5000",
            "descuento_total": "0",
            "notas": "Venta de prueba",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "recibo" in resp.headers["location"]

        # Verificar venta creada
        venta = db.query(models.Venta).first()
        assert venta is not None
        assert venta.total == 3000.0
        assert venta.metodo_pago == "EFECTIVO"
        assert venta.cambio == 2000.0

        # Verificar stock descontado
        db.refresh(sample_producto)
        assert sample_producto.stock_actual == stock_inicial - 2

        # Verificar movimiento de inventario
        mov = db.query(models.MovimientoInventario).filter_by(
            tipo="SALIDA", producto_id=sample_producto.id
        ).first()
        assert mov is not None
        assert mov.cantidad == 2

    def test_venta_carrito_vacio(self, admin_client):
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": "[]",
            "cliente_id": "",
            "cliente_nombre": "Consumidor Final",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "0",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_venta_json_invalido(self, admin_client):
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": "invalid json{{{",
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "0",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_venta_stock_insuficiente(self, admin_client, sample_producto):
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 9999,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "0",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_venta_con_caja_abierta(self, admin_client, db, sample_producto, caja_abierta):
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Consumidor Final",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        })
        # Verificar movimiento de caja
        mov_caja = db.query(models.MovimientoCaja).filter_by(
            caja_id=caja_abierta.id, tipo="INGRESO"
        ).first()
        assert mov_caja is not None
        assert mov_caja.monto == 1500.0


class TestHistorialVentas:
    def test_historial_vacio(self, admin_client):
        resp = admin_client.get("/ventas")
        assert resp.status_code == 200

    def test_historial_con_filtros(self, admin_client):
        resp = admin_client.get("/ventas?fecha_desde=2025-01-01&fecha_hasta=2030-12-31")
        assert resp.status_code == 200


class TestDetalleVenta:
    def _crear_venta(self, admin_client, sample_producto):
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Consumidor Final",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        })

    def test_detalle_ok(self, admin_client, db, sample_producto):
        self._crear_venta(admin_client, sample_producto)
        venta = db.query(models.Venta).first()
        resp = admin_client.get(f"/ventas/{venta.id}/detalle")
        assert resp.status_code == 200

    def test_recibo_ok(self, admin_client, db, sample_producto, sample_config):
        self._crear_venta(admin_client, sample_producto)
        venta = db.query(models.Venta).first()
        resp = admin_client.get(f"/ventas/{venta.id}/recibo")
        assert resp.status_code == 200

    def test_detalle_inexistente(self, admin_client):
        resp = admin_client.get("/ventas/9999/detalle", follow_redirects=False)
        assert resp.status_code == 303


class TestAnularVenta:
    def test_anular_ok(self, admin_client, db, sample_producto):
        stock_pre = sample_producto.stock_actual
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 3,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "5000",
            "descuento_total": "0",
            "notas": "",
        })
        venta = db.query(models.Venta).first()
        db.refresh(sample_producto)
        assert sample_producto.stock_actual == stock_pre - 3

        resp = admin_client.post(f"/ventas/{venta.id}/anular", follow_redirects=False)
        assert resp.status_code == 303

        db.refresh(venta)
        assert venta.estado == "ANULADA"

        db.refresh(sample_producto)
        assert sample_producto.stock_actual == stock_pre

    def test_anular_vendedor_no_puede(self, vendedor_client, db, sample_producto):
        # Primero crear la venta como vendedor
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        vendedor_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        })
        venta = db.query(models.Venta).first()
        if venta:
            resp = vendedor_client.post(f"/ventas/{venta.id}/anular", follow_redirects=False)
            assert resp.status_code == 303
            assert "error" in resp.headers["location"].lower()
