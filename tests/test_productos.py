"""Tests para el modulo de productos (CRUD, filtros, stock)."""
import models


class TestListaProductos:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/productos")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_producto):
        resp = admin_client.get("/productos")
        assert resp.status_code == 200
        assert "Laptop Test" in resp.text

    def test_filtro_buscar(self, admin_client, sample_producto):
        resp = admin_client.get("/productos?buscar=Laptop")
        assert resp.status_code == 200
        assert "Laptop Test" in resp.text

    def test_filtro_buscar_sin_resultados(self, admin_client, sample_producto):
        resp = admin_client.get("/productos?buscar=NoExiste")
        assert resp.status_code == 200

    def test_filtro_categoria(self, admin_client, sample_producto):
        resp = admin_client.get(f"/productos?categoria_id={sample_producto.categoria_id}")
        assert resp.status_code == 200
        assert "Laptop Test" in resp.text

    def test_filtro_stock_bajo(self, admin_client, db, sample_categoria, sample_local):
        prod = models.Producto(
            codigo="LOW-001", nombre="Stock Bajo",
            precio_costo=100, precio_venta=200,
            stock_actual=2.0, stock_minimo=10.0,
            categoria_id=sample_categoria.id, activo=True,
            local_id=sample_local.id,
        )
        db.add(prod)
        db.commit()
        resp = admin_client.get("/productos?stock_bajo=true")
        assert resp.status_code == 200
        assert "Stock Bajo" in resp.text


class TestCrearProducto:
    def test_form_nuevo(self, admin_client):
        resp = admin_client.get("/productos/nuevo")
        assert resp.status_code == 200

    def test_crear_ok(self, admin_client, db, sample_categoria):
        resp = admin_client.post("/productos/nuevo", data={
            "codigo": "TEST-001",
            "nombre": "Producto Nuevo",
            "descripcion": "Desc",
            "categoria_id": str(sample_categoria.id),
            "proveedor_id": "",
            "precio_costo": "500",
            "precio_venta": "800",
            "stock_actual": "20",
            "stock_minimo": "3",
            "unidad_medida": "UND",
        }, follow_redirects=False)
        assert resp.status_code == 303
        prod = db.query(models.Producto).filter_by(codigo="TEST-001").first()
        assert prod is not None
        assert prod.nombre == "Producto Nuevo"
        assert prod.precio_venta == 800.0

    def test_crear_con_stock_genera_movimiento(self, admin_client, db, sample_categoria):
        admin_client.post("/productos/nuevo", data={
            "codigo": "MOV-001",
            "nombre": "Con Movimiento",
            "descripcion": "",
            "categoria_id": str(sample_categoria.id),
            "proveedor_id": "",
            "precio_costo": "100",
            "precio_venta": "200",
            "stock_actual": "15",
            "stock_minimo": "2",
            "unidad_medida": "UND",
        })
        prod = db.query(models.Producto).filter_by(codigo="MOV-001").first()
        mov = db.query(models.MovimientoInventario).filter_by(producto_id=prod.id).first()
        assert mov is not None
        assert mov.tipo == "ENTRADA"
        assert mov.cantidad == 15.0

    def test_crear_codigo_duplicado(self, admin_client, sample_producto):
        resp = admin_client.post("/productos/nuevo", data={
            "codigo": "PROD-001",
            "nombre": "Duplicado",
            "descripcion": "",
            "categoria_id": "",
            "proveedor_id": "",
            "precio_costo": "0",
            "precio_venta": "0",
            "stock_actual": "0",
            "stock_minimo": "0",
            "unidad_medida": "UND",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEditarProducto:
    def test_form_editar(self, admin_client, sample_producto):
        resp = admin_client.get(f"/productos/{sample_producto.id}/editar")
        assert resp.status_code == 200
        assert "Laptop Test" in resp.text

    def test_editar_ok(self, admin_client, db, sample_producto):
        resp = admin_client.post(f"/productos/{sample_producto.id}/editar", data={
            "codigo": "PROD-001",
            "nombre": "Laptop Actualizada",
            "descripcion": "Desc nueva",
            "categoria_id": str(sample_producto.categoria_id),
            "proveedor_id": str(sample_producto.proveedor_id),
            "precio_costo": "1100",
            "precio_venta": "1600",
            "stock_minimo": "10",
            "unidad_medida": "UND",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_producto)
        assert sample_producto.nombre == "Laptop Actualizada"
        assert sample_producto.precio_venta == 1600.0

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.get("/productos/9999/editar", follow_redirects=False)
        assert resp.status_code == 303

    def test_post_editar_inexistente(self, admin_client):
        """Cubre linea 167: POST editar producto que no existe."""
        resp = admin_client.post("/productos/9999/editar", data={
            "codigo": "NADA-001",
            "nombre": "No existe",
            "descripcion": "",
            "categoria_id": "",
            "proveedor_id": "",
            "precio_costo": "0",
            "precio_venta": "0",
            "stock_minimo": "0",
            "unidad_medida": "UND",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_post_editar_codigo_duplicado(self, admin_client, db, sample_producto, sample_categoria):
        """Cubre linea 174: POST editar con codigo que ya usa otro producto."""
        otro = models.Producto(
            codigo="OTRO-002",
            nombre="Otro Producto",
            precio_costo=50.0,
            precio_venta=80.0,
            stock_actual=5.0,
            stock_minimo=1.0,
            categoria_id=sample_categoria.id,
            activo=True,
        )
        db.add(otro)
        db.commit()
        # Intentar renombrar otro con el codigo de sample_producto
        resp = admin_client.post(f"/productos/{otro.id}/editar", data={
            "codigo": "PROD-001",  # codigo que ya usa sample_producto
            "nombre": "Otro Producto",
            "descripcion": "",
            "categoria_id": str(sample_categoria.id),
            "proveedor_id": "",
            "precio_costo": "50",
            "precio_venta": "80",
            "stock_minimo": "1",
            "unidad_medida": "UND",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarProducto:
    def test_eliminar_soft_delete(self, admin_client, db, sample_producto):
        resp = admin_client.post(
            f"/productos/{sample_producto.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_producto)
        assert sample_producto.activo is False

    def test_eliminar_inexistente(self, admin_client):
        resp = admin_client.post(
            "/productos/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestModeloProducto:
    def test_margen_calculo(self, sample_producto):
        assert sample_producto.margen == 50.0

    def test_margen_costo_cero(self, db):
        prod = models.Producto(
            codigo="ZERO-001", nombre="Gratis",
            precio_costo=0.0, precio_venta=100.0,
            stock_actual=1, stock_minimo=0, activo=True,
        )
        db.add(prod)
        db.commit()
        assert prod.margen == 0.0

    def test_stock_bajo_property(self, sample_producto):
        assert sample_producto.stock_bajo is False
        sample_producto.stock_actual = 3.0
        assert sample_producto.stock_bajo is True
