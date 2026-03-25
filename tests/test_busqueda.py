"""
Tests para verificar que las búsquedas y filtros en todos los módulos
funcionan correctamente, incluyendo el manejo de parámetros vacíos
que antes causaban errores 422 JSON de FastAPI.
"""
import pytest
from datetime import datetime, timedelta

import models


# ═══════════════════════════════════════════════════════════════
# PRODUCTOS
# ═══════════════════════════════════════════════════════════════

class TestBusquedaProductos:
    """Búsquedas y filtros en /productos."""

    def test_lista_sin_filtros(self, admin_client, sample_producto):
        r = admin_client.get("/productos")
        assert r.status_code == 200
        assert "Laptop Test" in r.text

    def test_buscar_por_nombre(self, admin_client, sample_producto):
        r = admin_client.get("/productos?buscar=Laptop")
        assert r.status_code == 200
        assert "Laptop Test" in r.text

    def test_buscar_por_codigo(self, admin_client, sample_producto):
        r = admin_client.get("/productos?buscar=PROD-001")
        assert r.status_code == 200
        assert "Laptop Test" in r.text

    def test_buscar_sin_resultados(self, admin_client, sample_producto):
        r = admin_client.get("/productos?buscar=NoExiste")
        assert r.status_code == 200
        assert "Laptop Test" not in r.text

    def test_filtro_categoria_valida(self, admin_client, sample_producto, sample_categoria):
        r = admin_client.get(f"/productos?categoria_id={sample_categoria.id}")
        assert r.status_code == 200
        assert "Laptop Test" in r.text

    def test_filtro_categoria_vacio(self, admin_client, sample_producto):
        """Parámetro categoria_id vacío (como lo envía un <select> con opción vacía)."""
        r = admin_client.get("/productos?categoria_id=")
        assert r.status_code == 200
        assert "Laptop Test" in r.text

    def test_filtro_stock_bajo_vacio(self, admin_client, sample_producto):
        """Parámetro stock_bajo vacío no debe causar error."""
        r = admin_client.get("/productos?stock_bajo=")
        assert r.status_code == 200

    def test_filtro_stock_bajo_true(self, admin_client, db, sample_categoria):
        prod = models.Producto(
            codigo="LOW-001", nombre="Stock Bajo", categoria_id=sample_categoria.id,
            precio_costo=100, precio_venta=200,
            stock_actual=2, stock_minimo=10, unidad_medida="UND", activo=True,
        )
        db.add(prod)
        db.commit()
        r = admin_client.get("/productos?stock_bajo=true")
        assert r.status_code == 200
        assert "Stock Bajo" in r.text

    def test_todos_parametros_vacios(self, admin_client, sample_producto):
        """Todos los parámetros de filtro vacíos (envío de formulario sin seleccionar nada)."""
        r = admin_client.get("/productos?buscar=&categoria_id=&stock_bajo=")
        assert r.status_code == 200
        assert "Laptop Test" in r.text

    def test_combinacion_busqueda_y_categoria(self, admin_client, sample_producto, sample_categoria):
        r = admin_client.get(f"/productos?buscar=Laptop&categoria_id={sample_categoria.id}")
        assert r.status_code == 200
        assert "Laptop Test" in r.text


# ═══════════════════════════════════════════════════════════════
# INVENTARIO
# ═══════════════════════════════════════════════════════════════

class TestBusquedaInventario:
    """Búsquedas y filtros en /inventario."""

    def _crear_movimiento(self, db, producto):
        mov = models.MovimientoInventario(
            producto_id=producto.id, tipo="ENTRADA", cantidad=10,
            stock_anterior=40, stock_resultante=50, precio_unitario=1000,
            observaciones="Test", fecha=datetime.now(),
        )
        db.add(mov)
        db.commit()
        return mov

    def test_lista_sin_filtros(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario")
        assert r.status_code == 200

    def test_filtro_producto_id_vacio(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario?producto_id=")
        assert r.status_code == 200

    def test_filtro_producto_id_valido(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get(f"/inventario?producto_id={sample_producto.id}")
        assert r.status_code == 200

    def test_filtro_tipo(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario?tipo=ENTRADA")
        assert r.status_code == 200

    def test_filtro_tipo_vacio(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario?tipo=")
        assert r.status_code == 200

    def test_pagina_vacia(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario?pagina=")
        assert r.status_code == 200

    def test_pagina_valida(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario?pagina=1")
        assert r.status_code == 200

    def test_todos_filtros_vacios(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        r = admin_client.get("/inventario?producto_id=&tipo=&fecha_desde=&fecha_hasta=&pagina=")
        assert r.status_code == 200

    def test_filtro_fechas(self, admin_client, sample_producto, db):
        self._crear_movimiento(db, sample_producto)
        hoy = datetime.now().strftime("%Y-%m-%d")
        r = admin_client.get(f"/inventario?fecha_desde={hoy}&fecha_hasta={hoy}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# VENTAS
# ═══════════════════════════════════════════════════════════════

class TestBusquedaVentas:
    """Búsquedas y filtros en /ventas."""

    def test_historial_sin_filtros(self, admin_client):
        r = admin_client.get("/ventas")
        assert r.status_code == 200

    def test_historial_pagina_vacia(self, admin_client):
        r = admin_client.get("/ventas?pagina=")
        assert r.status_code == 200

    def test_historial_estado_vacio(self, admin_client):
        r = admin_client.get("/ventas?estado=")
        assert r.status_code == 200

    def test_historial_buscar(self, admin_client):
        r = admin_client.get("/ventas?buscar=VTA")
        assert r.status_code == 200

    def test_historial_todos_vacios(self, admin_client):
        r = admin_client.get("/ventas?fecha_desde=&fecha_hasta=&estado=&buscar=&pagina=")
        assert r.status_code == 200

    def test_historial_filtro_fechas(self, admin_client):
        hoy = datetime.now().strftime("%Y-%m-%d")
        r = admin_client.get(f"/ventas?fecha_desde={hoy}&fecha_hasta={hoy}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# CAJA
# ═══════════════════════════════════════════════════════════════

class TestBusquedaCaja:
    """Filtros en /caja/historial."""

    def test_historial_sin_filtros(self, admin_client):
        r = admin_client.get("/caja/historial")
        assert r.status_code == 200

    def test_historial_pagina_vacia(self, admin_client):
        r = admin_client.get("/caja/historial?pagina=")
        assert r.status_code == 200

    def test_historial_pagina_valida(self, admin_client):
        r = admin_client.get("/caja/historial?pagina=1")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# REPORTES
# ═══════════════════════════════════════════════════════════════

class TestBusquedaReportes:
    """Filtros en /reportes/*."""

    def test_stock_sin_filtros(self, admin_client):
        r = admin_client.get("/reportes/stock")
        assert r.status_code == 200

    def test_stock_categoria_vacia(self, admin_client, sample_producto):
        r = admin_client.get("/reportes/stock?categoria_id=")
        assert r.status_code == 200

    def test_stock_solo_bajo_vacio(self, admin_client, sample_producto):
        r = admin_client.get("/reportes/stock?solo_bajo=")
        assert r.status_code == 200

    def test_stock_solo_bajo_true(self, admin_client, sample_producto):
        r = admin_client.get("/reportes/stock?solo_bajo=true")
        assert r.status_code == 200

    def test_stock_todos_vacios(self, admin_client, sample_producto):
        r = admin_client.get("/reportes/stock?categoria_id=&solo_bajo=")
        assert r.status_code == 200

    def test_stock_con_categoria_valida(self, admin_client, sample_producto, sample_categoria):
        r = admin_client.get(f"/reportes/stock?categoria_id={sample_categoria.id}")
        assert r.status_code == 200

    def test_movimientos_sin_filtros(self, admin_client):
        r = admin_client.get("/reportes/movimientos")
        assert r.status_code == 200

    def test_movimientos_categoria_vacia(self, admin_client):
        r = admin_client.get("/reportes/movimientos?categoria_id=")
        assert r.status_code == 200

    def test_movimientos_todos_vacios(self, admin_client):
        r = admin_client.get("/reportes/movimientos?fecha_desde=&fecha_hasta=&tipo=&categoria_id=")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# DEUDAS
# ═══════════════════════════════════════════════════════════════

class TestBusquedaDeudas:
    """Búsquedas y filtros en /deudas."""

    def test_lista_sin_filtros(self, admin_client):
        r = admin_client.get("/deudas")
        assert r.status_code == 200

    def test_buscar_vacio(self, admin_client):
        r = admin_client.get("/deudas?buscar=")
        assert r.status_code == 200

    def test_estado_vacio(self, admin_client):
        r = admin_client.get("/deudas?estado=")
        assert r.status_code == 200

    def test_acreedor_tipo_vacio(self, admin_client):
        r = admin_client.get("/deudas?acreedor_tipo=")
        assert r.status_code == 200

    def test_todos_vacios(self, admin_client):
        r = admin_client.get("/deudas?estado=&acreedor_tipo=&buscar=")
        assert r.status_code == 200

    def test_buscar_por_nombre(self, admin_client, sample_deuda):
        r = admin_client.get("/deudas?buscar=Proveedor")
        assert r.status_code == 200

    def test_filtro_estado(self, admin_client, sample_deuda):
        r = admin_client.get("/deudas?estado=PENDIENTE")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# FACTURAS
# ═══════════════════════════════════════════════════════════════

class TestBusquedaFacturas:
    """Búsquedas y filtros en /facturas."""

    def test_lista_sin_filtros(self, admin_client):
        r = admin_client.get("/facturas")
        assert r.status_code == 200

    def test_buscar_vacio(self, admin_client):
        r = admin_client.get("/facturas?buscar=")
        assert r.status_code == 200

    def test_estado_vacio(self, admin_client):
        r = admin_client.get("/facturas?estado=")
        assert r.status_code == 200

    def test_todos_vacios(self, admin_client):
        r = admin_client.get("/facturas?estado=&buscar=")
        assert r.status_code == 200

    def test_buscar_por_nombre(self, admin_client, sample_factura):
        r = admin_client.get("/facturas?buscar=Cliente")
        assert r.status_code == 200
        assert "Cliente Factura Test" in r.text


# ═══════════════════════════════════════════════════════════════
# ACREEDORES
# ═══════════════════════════════════════════════════════════════

class TestBusquedaAcreedores:
    """Búsquedas y filtros en /acreedores."""

    def _crear_acreedor(self, db):
        acr = models.Acreedor(
            nombre="Acreedor Test", tipo="PROVEEDOR",
            documento="123", activo=True,
        )
        db.add(acr)
        db.commit()
        return acr

    def test_lista_sin_filtros(self, admin_client, db):
        self._crear_acreedor(db)
        r = admin_client.get("/acreedores")
        assert r.status_code == 200

    def test_buscar_vacio(self, admin_client, db):
        self._crear_acreedor(db)
        r = admin_client.get("/acreedores?buscar=")
        assert r.status_code == 200

    def test_tipo_vacio(self, admin_client, db):
        self._crear_acreedor(db)
        r = admin_client.get("/acreedores?tipo=")
        assert r.status_code == 200

    def test_todos_vacios(self, admin_client, db):
        self._crear_acreedor(db)
        r = admin_client.get("/acreedores?buscar=&tipo=")
        assert r.status_code == 200

    def test_buscar_por_nombre(self, admin_client, db):
        self._crear_acreedor(db)
        r = admin_client.get("/acreedores?buscar=Acreedor")
        assert r.status_code == 200
        assert "Acreedor Test" in r.text

    def test_filtro_tipo(self, admin_client, db):
        self._crear_acreedor(db)
        r = admin_client.get("/acreedores?tipo=PROVEEDOR")
        assert r.status_code == 200
        assert "Acreedor Test" in r.text
