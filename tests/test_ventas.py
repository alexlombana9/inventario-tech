"""Tests para el modulo de ventas/POS (procesar, historial, anular, recibo)."""
import json
import models
from datetime import date, timedelta


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


class TestPOSNoHayCaja:
    """Cubre linea 111 — POS con producto no encontrado en items."""

    def test_pos_page_sin_caja(self, admin_client, sample_producto):
        """POS renderiza correctamente aunque no haya caja abierta (caja_abierta=None)."""
        resp = admin_client.get("/ventas/pos")
        assert resp.status_code == 200

    def test_venta_producto_inexistente(self, admin_client):
        """Linea 111: producto_id no existe en DB → redirect con error."""
        items = json.dumps([{
            "producto_id": 99999,
            "nombre": "Fantasma",
            "cantidad": 1,
            "precio_unitario": 100.0,
            "descuento": 0,
        }])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "500",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestVentaTotalNegativo:
    """Cubre linea 123 — total < 0 se convierte a 0."""

    def test_descuento_mayor_al_total(self, admin_client, db, sample_producto):
        """Descuento total supera el subtotal → total=0, venta se crea OK."""
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 100.0,
            "descuento": 0,
        }])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "0",
            "descuento_total": "500",  # descuento mayor al subtotal
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        venta = db.query(models.Venta).first()
        assert venta is not None
        assert venta.total == 0.0


class TestVentaErrorTransaccion:
    """Cubre lineas 163-165 y 214-216 — rollback en error de transaccion."""

    def test_stock_insuficiente_en_transaccion(self, admin_client, db, sample_producto):
        """Lineas 163-165: durante la transaccion, stock baja a 0 entre la validacion y el with_for_update.
        Simulamos poniendo stock_actual=0 directamente antes de procesar."""
        # Pasamos la validacion inicial con stock suficiente
        # pero durante la transaccion el with_for_update encuentra stock=0
        sample_producto.stock_actual = 1
        db.commit()

        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        # Primera venta consume el stock
        admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test1",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        })
        # Segunda venta con el mismo item — stock ahora es 0
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test2",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestHistorialFiltrosExtra:
    """Cubre lineas 257, 261, 263-267 — filtros adicionales del historial."""

    def test_historial_filtro_metodo_pago(self, admin_client, db, sample_producto):
        """Linea 262: filtro metodo_pago."""
        resp = admin_client.get("/ventas?metodo_pago=EFECTIVO")
        assert resp.status_code == 200

    def test_historial_filtro_vendedor_invalido(self, admin_client):
        """Linea 264-268: vendedor_id no numerico se ignora con ValueError."""
        resp = admin_client.get("/ventas?vendedor_id=abc")
        assert resp.status_code == 200

    def test_historial_filtro_vendedor_valido(self, admin_client, admin_user):
        """Linea 264-266: vendedor_id numerico valido."""
        resp = admin_client.get(f"/ventas?vendedor_id={admin_user.id}")
        assert resp.status_code == 200

    def test_historial_filtro_estado(self, admin_client):
        """Linea 260-261: filtro por estado."""
        resp = admin_client.get("/ventas?estado=COMPLETADA")
        assert resp.status_code == 200

    def test_historial_buscar(self, admin_client):
        """Linea 269-273: busqueda por numero/cliente."""
        resp = admin_client.get("/ventas?buscar=VTA")
        assert resp.status_code == 200

    def test_historial_fecha_invalida(self, admin_client):
        """Linea 257 (except ValueError): fecha con formato invalido."""
        resp = admin_client.get("/ventas?fecha_desde=no-date&fecha_hasta=no-date")
        assert resp.status_code == 200


class TestVentasExcel:
    """Cubre lineas 319-369 — exportacion Excel de ventas."""

    def test_excel_sin_datos(self, admin_client):
        """Excel con tabla vacia."""
        resp = admin_client.get("/ventas/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_excel_con_datos(self, admin_client, db, sample_producto):
        """Excel con ventas existentes."""
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
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        })
        resp = admin_client.get("/ventas/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_excel_con_filtro_estado(self, admin_client):
        """Excel filtrado por estado."""
        resp = admin_client.get("/ventas/excel?estado=COMPLETADA")
        assert resp.status_code == 200

    def test_excel_con_fechas(self, admin_client):
        """Excel filtrado por rango de fechas."""
        hoy = date.today().strftime("%Y-%m-%d")
        resp = admin_client.get(f"/ventas/excel?fecha_desde={hoy}&fecha_hasta={hoy}")
        assert resp.status_code == 200


class TestReciboNoExiste:
    """Cubre linea 409 — recibo de venta inexistente."""

    def test_recibo_inexistente(self, admin_client):
        """Linea 409: venta no encontrada en recibo → redirect 303."""
        resp = admin_client.get("/ventas/9999/recibo", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestAnularVentaEdgeCases:
    """Cubre lineas 435, 437 — anular venta inexistente y ya anulada."""

    def test_anular_inexistente(self, admin_client):
        """Linea 435: venta no existe → redirect con error."""
        resp = admin_client.post("/ventas/9999/anular", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_anular_ya_anulada(self, admin_client, db, sample_producto):
        """Linea 437: venta ya anulada → redirect con error."""
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
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        })
        venta = db.query(models.Venta).first()
        # Anular por primera vez
        admin_client.post(f"/ventas/{venta.id}/anular")
        # Intentar anular de nuevo
        resp = admin_client.post(f"/ventas/{venta.id}/anular", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_anular_restaura_stock_con_caja(self, admin_client, db, sample_producto, caja_abierta):
        """Lineas 263-267: anular venta con caja abierta restaura stock correctamente."""
        stock_inicial = sample_producto.stock_actual
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 2,
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
        resp = admin_client.post(f"/ventas/{venta.id}/anular", follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_producto)
        assert sample_producto.stock_actual == stock_inicial

    def test_venta_metodo_no_efectivo_sin_caja(self, admin_client, db, sample_producto):
        """Linea 125: metodo_pago != EFECTIVO → cambio=0."""
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "TARJETA",
            "monto_recibido": "5000",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        venta = db.query(models.Venta).first()
        assert venta is not None
        assert venta.cambio == 0.0


class TestVentasExcelFechaInvalida:
    """Cubre linea 341 — except ValueError en Excel export."""

    def test_excel_fecha_invalida(self, admin_client):
        """Linea 341: fecha con formato invalido → ValueError se captura, continua."""
        resp = admin_client.get("/ventas/excel?fecha_desde=no-date&fecha_hasta=no-date")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]


class TestVentaExceptionHandler:
    """Cubre lineas 214-216 — except Exception en transaccion de venta."""

    def test_cliente_id_invalido_causa_exception(self, admin_client, db, sample_producto):
        """Lineas 214-216: cliente_id no numerico causa ValueError dentro del try,
        capturado por except Exception → rollback y redirect con error."""
        items = json.dumps([{
            "producto_id": sample_producto.id,
            "nombre": sample_producto.nombre,
            "cantidad": 1,
            "precio_unitario": 1500.0,
            "descuento": 0,
        }])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "no-es-un-numero",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "2000",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestVentaStockTransaccion:
    """Cubre lineas 163-165 — stock insuficiente detectado dentro de la transaccion."""

    def test_doble_item_mismo_producto_excede_stock(self, admin_client, db, sample_producto):
        """Lineas 163-165: dos items con el mismo producto cuya cantidad combinada
        supera el stock. La prevalidacion pasa (cada item individual < stock),
        pero la segunda iteracion del with_for_update falla al ver stock reducido."""
        sample_producto.stock_actual = 3
        db.commit()

        # Dos entradas del mismo producto, cada una pide 2 unidades
        # Prevalidacion: 2 <= 3 OK para cada una individualmente
        # Transaccion: primera reduce stock a 1, segunda falla (1 < 2)
        items = json.dumps([
            {
                "producto_id": sample_producto.id,
                "nombre": sample_producto.nombre,
                "cantidad": 2,
                "precio_unitario": 1500.0,
                "descuento": 0,
            },
            {
                "producto_id": sample_producto.id,
                "nombre": sample_producto.nombre,
                "cantidad": 2,
                "precio_unitario": 1500.0,
                "descuento": 0,
            },
        ])
        resp = admin_client.post("/ventas/procesar", data={
            "items_json": items,
            "cliente_id": "",
            "cliente_nombre": "Test",
            "metodo_pago": "EFECTIVO",
            "monto_recibido": "10000",
            "descuento_total": "0",
            "notas": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        # Debe redirigir con error de stock insuficiente
        assert "error" in resp.headers["location"].lower()
