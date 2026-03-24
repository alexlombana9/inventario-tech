"""Tests para el modulo de inventario (movimientos: entrada, salida, ajuste)."""
import models


class TestListaMovimientos:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/inventario")
        assert resp.status_code == 200

    def test_lista_con_paginacion(self, admin_client, sample_producto):
        resp = admin_client.get("/inventario?pagina=1")
        assert resp.status_code == 200


class TestFormsMovimientos:
    def test_form_entrada(self, admin_client):
        resp = admin_client.get("/inventario/entrada")
        assert resp.status_code == 200

    def test_form_salida(self, admin_client):
        resp = admin_client.get("/inventario/salida")
        assert resp.status_code == 200

    def test_form_ajuste(self, admin_client):
        resp = admin_client.get("/inventario/ajuste")
        assert resp.status_code == 200


class TestRegistrarEntrada:
    def test_entrada_ok(self, admin_client, db, sample_producto):
        stock_inicial = sample_producto.stock_actual
        resp = admin_client.post("/inventario/registrar", data={
            "producto_id": str(sample_producto.id),
            "tipo": "ENTRADA",
            "cantidad": "10",
            "precio_unitario": "1000",
            "proveedor_id": str(sample_producto.proveedor_id),
            "numero_referencia": "FAC-EXT-001",
            "observaciones": "Entrada de prueba",
            "fecha": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_producto)
        assert sample_producto.stock_actual == stock_inicial + 10

        mov = db.query(models.MovimientoInventario).filter_by(
            producto_id=sample_producto.id, tipo="ENTRADA"
        ).first()
        assert mov is not None
        assert mov.cantidad == 10.0
        assert mov.stock_resultante == stock_inicial + 10

    def test_entrada_cantidad_cero_rechazada(self, admin_client, sample_producto):
        resp = admin_client.post("/inventario/registrar", data={
            "producto_id": str(sample_producto.id),
            "tipo": "ENTRADA",
            "cantidad": "0",
            "precio_unitario": "0",
            "proveedor_id": "",
            "numero_referencia": "",
            "observaciones": "",
            "fecha": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_entrada_producto_inexistente(self, admin_client):
        resp = admin_client.post("/inventario/registrar", data={
            "producto_id": "9999",
            "tipo": "ENTRADA",
            "cantidad": "5",
            "precio_unitario": "100",
            "proveedor_id": "",
            "numero_referencia": "",
            "observaciones": "",
            "fecha": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestRegistrarSalida:
    def test_salida_ok(self, admin_client, db, sample_producto):
        stock_inicial = sample_producto.stock_actual
        resp = admin_client.post("/inventario/registrar", data={
            "producto_id": str(sample_producto.id),
            "tipo": "SALIDA",
            "cantidad": "5",
            "precio_unitario": "1500",
            "proveedor_id": "",
            "numero_referencia": "",
            "observaciones": "Salida test",
            "fecha": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_producto)
        assert sample_producto.stock_actual == stock_inicial - 5

    def test_salida_stock_insuficiente(self, admin_client, sample_producto):
        resp = admin_client.post("/inventario/registrar", data={
            "producto_id": str(sample_producto.id),
            "tipo": "SALIDA",
            "cantidad": "9999",
            "precio_unitario": "0",
            "proveedor_id": "",
            "numero_referencia": "",
            "observaciones": "",
            "fecha": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestRegistrarAjuste:
    def test_ajuste_ok(self, admin_client, db, sample_producto):
        resp = admin_client.post("/inventario/ajuste/registrar", data={
            "producto_id": str(sample_producto.id),
            "nuevo_stock": "100",
            "observaciones": "Ajuste por conteo fisico",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_producto)
        assert sample_producto.stock_actual == 100.0

    def test_ajuste_producto_inexistente(self, admin_client):
        resp = admin_client.post("/inventario/ajuste/registrar", data={
            "producto_id": "9999",
            "nuevo_stock": "10",
            "observaciones": "",
        }, follow_redirects=False)
        assert resp.status_code == 303


class TestFiltrosMovimientos:
    def test_filtro_por_tipo(self, admin_client, db, sample_producto):
        # Crear un movimiento de entrada
        admin_client.post("/inventario/registrar", data={
            "producto_id": str(sample_producto.id),
            "tipo": "ENTRADA",
            "cantidad": "5",
            "precio_unitario": "100",
            "proveedor_id": "",
            "numero_referencia": "",
            "observaciones": "",
            "fecha": "",
        })
        resp = admin_client.get("/inventario?tipo=ENTRADA")
        assert resp.status_code == 200

    def test_filtro_por_producto(self, admin_client, sample_producto):
        resp = admin_client.get(f"/inventario?producto_id={sample_producto.id}")
        assert resp.status_code == 200
