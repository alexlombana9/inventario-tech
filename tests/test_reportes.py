"""Tests para el modulo de reportes (stock, movimientos)."""
from datetime import datetime
import models


class TestReportesIndex:
    def test_index_redirige_a_stock(self, admin_client):
        resp = admin_client.get("/reportes", follow_redirects=False)
        assert resp.status_code == 303
        assert "/reportes/stock" in resp.headers["location"]


class TestReporteStock:
    def test_stock_vacio(self, admin_client):
        resp = admin_client.get("/reportes/stock")
        assert resp.status_code == 200

    def test_stock_con_productos(self, admin_client, sample_producto):
        resp = admin_client.get("/reportes/stock")
        assert resp.status_code == 200
        assert "Laptop Test" in resp.text

    def test_stock_filtro_categoria(self, admin_client, sample_producto, sample_categoria):
        resp = admin_client.get(f"/reportes/stock?categoria_id={sample_categoria.id}")
        assert resp.status_code == 200
        assert "Laptop Test" in resp.text

    def test_stock_filtro_categoria_sin_resultados(self, admin_client, sample_producto):
        resp = admin_client.get("/reportes/stock?categoria_id=9999")
        assert resp.status_code == 200
        assert "Laptop Test" not in resp.text

    def test_stock_filtro_solo_bajo(self, admin_client, db, sample_producto):
        """Producto con stock suficiente no aparece con filtro solo_bajo."""
        resp = admin_client.get("/reportes/stock?solo_bajo=true")
        assert resp.status_code == 200
        # sample_producto tiene stock_actual=50, stock_minimo=5, no es bajo
        assert "Laptop Test" not in resp.text

    def test_stock_producto_bajo_aparece(self, admin_client, db, sample_categoria, sample_proveedor, sample_local):
        """Producto con stock bajo aparece con filtro solo_bajo."""
        prod_bajo = models.Producto(
            codigo="BAJO-001",
            nombre="Producto Bajo Stock",
            categoria_id=sample_categoria.id,
            proveedor_id=sample_proveedor.id,
            precio_costo=100.0,
            precio_venta=200.0,
            stock_actual=2.0,
            stock_minimo=10.0,
            unidad_medida="UND",
            activo=True,
            local_id=sample_local.id,
        )
        db.add(prod_bajo)
        db.commit()

        resp = admin_client.get("/reportes/stock?solo_bajo=true")
        assert resp.status_code == 200
        assert "Producto Bajo Stock" in resp.text


class TestReporteMovimientos:
    def test_movimientos_vacio(self, admin_client):
        resp = admin_client.get("/reportes/movimientos")
        assert resp.status_code == 200

    def test_movimientos_con_datos(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="ENTRADA",
            cantidad=10,
            stock_anterior=50,
            stock_resultante=60,
            precio_unitario=1000.0,
            observaciones="Entrada de prueba",
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()

        resp = admin_client.get("/reportes/movimientos")
        assert resp.status_code == 200

    def test_movimientos_filtro_tipo(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="SALIDA",
            cantidad=5,
            stock_anterior=50,
            stock_resultante=45,
            precio_unitario=1000.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()

        resp = admin_client.get("/reportes/movimientos?tipo=SALIDA")
        assert resp.status_code == 200

    def test_movimientos_filtro_fechas(self, admin_client):
        resp = admin_client.get(
            "/reportes/movimientos?fecha_desde=2026-01-01&fecha_hasta=2026-12-31"
        )
        assert resp.status_code == 200

    def test_movimientos_filtro_categoria(self, admin_client, db, sample_producto, sample_categoria):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="ENTRADA",
            cantidad=5,
            stock_anterior=50,
            stock_resultante=55,
            precio_unitario=1000.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()

        resp = admin_client.get(f"/reportes/movimientos?categoria_id={sample_categoria.id}")
        assert resp.status_code == 200


class TestReportesExcel:
    def test_stock_excel(self, admin_client, sample_producto):
        resp = admin_client.get("/reportes/stock/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_stock_excel_sin_productos(self, admin_client):
        resp = admin_client.get("/reportes/stock/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_stock_excel_con_filtro_categoria(self, admin_client, sample_producto, sample_categoria):
        resp = admin_client.get(f"/reportes/stock/excel?categoria_id={sample_categoria.id}")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_stock_excel_con_filtro_solo_bajo(self, admin_client, db, sample_categoria, sample_proveedor):
        prod_bajo = models.Producto(
            codigo="BAJO-EXCEL",
            nombre="Producto Bajo Excel",
            categoria_id=sample_categoria.id,
            proveedor_id=sample_proveedor.id,
            precio_costo=100.0,
            precio_venta=200.0,
            stock_actual=1.0,
            stock_minimo=10.0,
            unidad_medida="UND",
            activo=True,
        )
        db.add(prod_bajo)
        db.commit()
        resp = admin_client.get("/reportes/stock/excel?solo_bajo=true")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_stock_excel_filename_en_header(self, admin_client):
        resp = admin_client.get("/reportes/stock/excel")
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert ".xlsx" in resp.headers.get("content-disposition", "")

    def test_movimientos_excel(self, admin_client):
        resp = admin_client.get("/reportes/movimientos/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_movimientos_excel_con_datos(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="ENTRADA",
            cantidad=10,
            stock_anterior=50,
            stock_resultante=60,
            precio_unitario=1000.0,
            observaciones="Entrada Excel",
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/reportes/movimientos/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_movimientos_excel_con_filtro_tipo(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="SALIDA",
            cantidad=5,
            stock_anterior=50,
            stock_resultante=45,
            precio_unitario=1500.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/reportes/movimientos/excel?tipo=SALIDA")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_movimientos_excel_con_fechas(self, admin_client):
        resp = admin_client.get(
            "/reportes/movimientos/excel?fecha_desde=2026-01-01&fecha_hasta=2026-12-31"
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_movimientos_excel_filename_en_header(self, admin_client):
        resp = admin_client.get(
            "/reportes/movimientos/excel?fecha_desde=2026-01-01&fecha_hasta=2026-12-31"
        )
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert ".xlsx" in resp.headers.get("content-disposition", "")

    def test_movimientos_excel_tipo_ajuste(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="AJUSTE",
            cantidad=3,
            stock_anterior=50,
            stock_resultante=53,
            precio_unitario=0.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/reportes/movimientos/excel?tipo=AJUSTE")
        assert resp.status_code == 200


class TestReportesPDF:
    def test_stock_pdf(self, admin_client, sample_producto):
        resp = admin_client.get("/reportes/stock/pdf")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_stock_pdf_vacio(self, admin_client):
        resp = admin_client.get("/reportes/stock/pdf")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_stock_pdf_con_filtro_categoria(self, admin_client, sample_producto, sample_categoria):
        resp = admin_client.get(f"/reportes/stock/pdf?categoria_id={sample_categoria.id}")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_stock_pdf_con_filtro_solo_bajo(self, admin_client, db, sample_categoria, sample_proveedor):
        prod_bajo = models.Producto(
            codigo="BAJO-PDF",
            nombre="Producto Bajo PDF",
            categoria_id=sample_categoria.id,
            proveedor_id=sample_proveedor.id,
            precio_costo=50.0,
            precio_venta=100.0,
            stock_actual=1.0,
            stock_minimo=20.0,
            unidad_medida="UND",
            activo=True,
        )
        db.add(prod_bajo)
        db.commit()
        resp = admin_client.get("/reportes/stock/pdf?solo_bajo=true")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_movimientos_pdf(self, admin_client):
        resp = admin_client.get("/reportes/movimientos/pdf")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_movimientos_pdf_con_datos(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="ENTRADA",
            cantidad=5,
            stock_anterior=50,
            stock_resultante=55,
            precio_unitario=1000.0,
            observaciones="PDF test",
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/reportes/movimientos/pdf")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_movimientos_pdf_con_fechas(self, admin_client):
        resp = admin_client.get(
            "/reportes/movimientos/pdf?fecha_desde=2026-01-01&fecha_hasta=2026-12-31"
        )
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_movimientos_pdf_con_tipo(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="SALIDA",
            cantidad=2,
            stock_anterior=50,
            stock_resultante=48,
            precio_unitario=1500.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/reportes/movimientos/pdf?tipo=SALIDA")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_movimientos_pdf_fecha_invalida(self, admin_client):
        """Fecha invalida en PDF no debe crashear (except ValueError en router)."""
        resp = admin_client.get(
            "/reportes/movimientos/pdf?fecha_desde=notadate&fecha_hasta=alsonotadate"
        )
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")

    def test_movimientos_pdf_tipo_ajuste(self, admin_client, db, sample_producto):
        """AJUSTE tipo para colorear fila en PDF."""
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="AJUSTE",
            cantidad=3,
            stock_anterior=50,
            stock_resultante=53,
            precio_unitario=0.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get("/reportes/movimientos/pdf?tipo=AJUSTE")
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "")


class TestReporteMovimientosFiltrosAvanzados:
    def test_movimientos_filtro_fecha_invalida(self, admin_client):
        """Fecha invalida no debe crashear (except ValueError en router)."""
        resp = admin_client.get(
            "/reportes/movimientos?fecha_desde=invalido&fecha_hasta=tambien_invalido"
        )
        assert resp.status_code == 200

    def test_movimientos_filtro_producto_especifico(self, admin_client, db, sample_producto):
        mov = models.MovimientoInventario(
            producto_id=sample_producto.id,
            tipo="ENTRADA",
            cantidad=15,
            stock_anterior=50,
            stock_resultante=65,
            precio_unitario=1000.0,
            fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        resp = admin_client.get(f"/reportes/movimientos?categoria_id={sample_producto.categoria_id}")
        assert resp.status_code == 200

    def test_movimientos_excel_fecha_invalida(self, admin_client):
        """Fecha invalida en Excel tampoco debe crashear."""
        resp = admin_client.get(
            "/reportes/movimientos/excel?fecha_desde=invalido&fecha_hasta=invalido"
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_stock_excel_categoria_invalida(self, admin_client, sample_producto):
        """categoria_id inexistente devuelve Excel sin filas de datos."""
        resp = admin_client.get("/reportes/stock/excel?categoria_id=9999")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")
