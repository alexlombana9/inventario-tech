"""Tests para el modulo de importacion Excel."""
import io
import models


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_excel(headers: list, rows: list = None) -> bytes:
    """Genera un archivo Excel en memoria con los headers y filas dados."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    if rows:
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _post_import(client, tipo: str, content: bytes, filename: str = "test.xlsx"):
    """Envia una solicitud POST /importar/procesar con el archivo dado."""
    files = {"archivo": (filename, io.BytesIO(content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"tipo": tipo}
    return client.post("/importar/procesar", data=data, files=files, follow_redirects=False)


# ── Acceso ───────────────────────────────────────────────────────────────────

class TestAccesoImportar:
    def test_admin_puede_acceder(self, admin_client):
        resp = admin_client.get("/importar")
        assert resp.status_code == 200

    def test_vendedor_no_puede_acceder(self, vendedor_client):
        resp = vendedor_client.get("/importar", follow_redirects=False)
        assert resp.status_code in (303, 403)


# ── Descargar Plantillas ─────────────────────────────────────────────────────

class TestDescargarPlantillas:
    def test_plantilla_productos(self, admin_client):
        resp = admin_client.get("/importar/plantilla/productos")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_plantilla_categorias(self, admin_client):
        resp = admin_client.get("/importar/plantilla/categorias")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_plantilla_tipo_invalido(self, admin_client):
        resp = admin_client.get("/importar/plantilla/invalido", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


# ── Validaciones generales ───────────────────────────────────────────────────

class TestImportarValidacionesGenerales:
    def test_extension_invalida_rechazada(self, admin_client):
        files = {"archivo": ("test.csv", io.BytesIO(b"col1,col2\nval1,val2"), "text/csv")}
        data = {"tipo": "categorias"}
        resp = admin_client.post("/importar/procesar", data=data, files=files, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_archivo_excel_invalido(self, admin_client):
        """Archivo con extension .xlsx pero contenido invalido."""
        files = {"archivo": ("bad.xlsx", io.BytesIO(b"esto no es excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"tipo": "categorias"}
        resp = admin_client.post("/importar/procesar", data=data, files=files, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_archivo_solo_encabezados_rechazado(self, admin_client):
        """Excel con solo una fila (sin datos) es rechazado."""
        content = _make_excel(["nombre", "descripcion"])
        resp = _post_import(admin_client, "categorias", content)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


# ── Importar Categorias ─────────────────────────────────────────────────────

class TestImportarCategorias:
    def test_importar_categoria_simple(self, admin_client, db):
        content = _make_excel(
            ["nombre", "descripcion"],
            [["Electronica", "Productos electronicos"]]
        )
        resp = _post_import(admin_client, "categorias", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        cat = db.query(models.Categoria).filter(models.Categoria.nombre == "Electronica").first()
        assert cat is not None
        assert cat.descripcion == "Productos electronicos"

    def test_importar_multiples_categorias(self, admin_client, db):
        content = _make_excel(
            ["nombre", "descripcion"],
            [
                ["Computadores", "Laptops y desktops"],
                ["Perifericos", "Teclados y mouse"],
                ["Audio", "Auriculares y parlantes"],
            ]
        )
        resp = _post_import(admin_client, "categorias", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        count = db.query(models.Categoria).count()
        assert count == 3

    def test_importar_categoria_duplicada_omitida(self, admin_client, db, sample_categoria):
        """Categoria con mismo nombre no se duplica."""
        content = _make_excel(
            ["nombre", "descripcion"],
            [[sample_categoria.nombre, "nueva desc"]]
        )
        resp = _post_import(admin_client, "categorias", content)
        assert resp.status_code == 303

        count = db.query(models.Categoria).filter(
            models.Categoria.nombre == sample_categoria.nombre
        ).count()
        assert count == 1

    def test_importar_categoria_sin_columna_nombre(self, admin_client):
        """Sin columna 'nombre', retorna error."""
        content = _make_excel(
            ["descripcion"],
            [["Solo descripcion"]]
        )
        resp = _post_import(admin_client, "categorias", content)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


# ── Importar Productos ───────────────────────────────────────────────────────

class TestImportarProductos:
    def test_importar_producto_nuevo(self, admin_client, db):
        content = _make_excel(
            ["codigo", "nombre", "precio_costo", "precio_venta", "stock_actual", "unidad_medida"],
            [["PROD-IMP-001", "Producto Importado", 5000, 10000, 20, "UND"]]
        )
        resp = _post_import(admin_client, "productos", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        prod = db.query(models.Producto).filter(models.Producto.codigo == "PROD-IMP-001").first()
        assert prod is not None
        assert prod.nombre == "Producto Importado"
        assert prod.precio_costo == 5000
        assert prod.precio_venta == 10000

    def test_importar_producto_sin_columnas_requeridas(self, admin_client):
        """Sin 'codigo' o 'nombre', retorna error."""
        content = _make_excel(
            ["precio_costo", "precio_venta"],
            [[5000, 10000]]
        )
        resp = _post_import(admin_client, "productos", content)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_importar_producto_actualiza_existente(self, admin_client, db, sample_producto):
        """Producto con mismo codigo se actualiza."""
        content = _make_excel(
            ["codigo", "nombre", "precio_venta"],
            [[sample_producto.codigo, "Nombre Actualizado", 9999]]
        )
        resp = _post_import(admin_client, "productos", content)
        assert resp.status_code == 303

        db.refresh(sample_producto)
        assert sample_producto.nombre == "Nombre Actualizado"
        assert sample_producto.precio_venta == 9999

    def test_importar_producto_crea_categoria_nueva(self, admin_client, db):
        """Si la categoria no existe, la crea automaticamente."""
        content = _make_excel(
            ["codigo", "nombre", "categoria", "precio_costo", "precio_venta"],
            [["PROD-CAT-NEW", "Prod con Cat Nueva", "CatNueva", 100, 200]]
        )
        resp = _post_import(admin_client, "productos", content)
        assert resp.status_code == 303

        cat = db.query(models.Categoria).filter(models.Categoria.nombre == "CatNueva").first()
        assert cat is not None

        prod = db.query(models.Producto).filter(models.Producto.codigo == "PROD-CAT-NEW").first()
        assert prod is not None
        assert prod.categoria_id == cat.id

    def test_importar_producto_con_stock_crea_movimiento(self, admin_client, db):
        content = _make_excel(
            ["codigo", "nombre", "precio_costo", "precio_venta", "stock_actual"],
            [["PROD-MOV", "Prod con Stock", 500, 1000, 25]]
        )
        resp = _post_import(admin_client, "productos", content)
        assert resp.status_code == 303

        prod = db.query(models.Producto).filter(models.Producto.codigo == "PROD-MOV").first()
        assert prod is not None

        mov = db.query(models.MovimientoInventario).filter(
            models.MovimientoInventario.producto_id == prod.id,
            models.MovimientoInventario.tipo == "ENTRADA",
        ).first()
        assert mov is not None
        assert mov.cantidad == 25


# ── Importar Clientes ────────────────────────────────────────────────────────

class TestImportarClientes:
    def test_importar_cliente_simple(self, admin_client, db):
        content = _make_excel(
            ["nombre", "tipo_documento", "documento", "telefono", "email"],
            [["Juan Perez", "CC", "1234567890", "3001234567", "juan@test.com"]]
        )
        resp = _post_import(admin_client, "clientes", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        cli = db.query(models.Cliente).filter(models.Cliente.documento == "1234567890").first()
        assert cli is not None
        assert cli.nombre == "Juan Perez"

    def test_importar_cliente_sin_columna_nombre(self, admin_client):
        content = _make_excel(
            ["documento", "telefono"],
            [["123456", "300123"]]
        )
        resp = _post_import(admin_client, "clientes", content)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_importar_cliente_duplicado_por_documento(self, admin_client, db, sample_cliente):
        """Cliente con mismo documento es omitido."""
        content = _make_excel(
            ["nombre", "documento"],
            [["Otro Nombre", sample_cliente.documento]]
        )
        resp = _post_import(admin_client, "clientes", content)
        assert resp.status_code == 303

        count = db.query(models.Cliente).filter(
            models.Cliente.documento == sample_cliente.documento
        ).count()
        assert count == 1


# ── Importar Proveedores ─────────────────────────────────────────────────────

class TestImportarProveedores:
    def test_importar_proveedor_simple(self, admin_client, db):
        content = _make_excel(
            ["nombre", "contacto", "telefono", "email", "nit_ruc"],
            [["Proveedor Importado", "Contacto X", "3001111111", "prov@test.com", "900111111-1"]]
        )
        resp = _post_import(admin_client, "proveedores", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        prov = db.query(models.Proveedor).filter(models.Proveedor.nombre == "Proveedor Importado").first()
        assert prov is not None
        assert prov.nit_ruc == "900111111-1"

    def test_importar_proveedor_duplicado_por_nombre(self, admin_client, db, sample_proveedor):
        content = _make_excel(
            ["nombre", "telefono"],
            [[sample_proveedor.nombre, "3009999999"]]
        )
        resp = _post_import(admin_client, "proveedores", content)
        assert resp.status_code == 303

        count = db.query(models.Proveedor).filter(
            models.Proveedor.nombre == sample_proveedor.nombre
        ).count()
        assert count == 1


# ── Importar Acreedores ──────────────────────────────────────────────────────

class TestImportarAcreedores:
    def test_importar_acreedor_simple(self, admin_client, db):
        content = _make_excel(
            ["nombre", "tipo", "documento", "telefono"],
            [["Acreedor Importado", "BANCO", "900222333-1", "6011111111"]]
        )
        resp = _post_import(admin_client, "acreedores", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        acr = db.query(models.Acreedor).filter(models.Acreedor.nombre == "Acreedor Importado").first()
        assert acr is not None
        assert acr.tipo == "BANCO"

    def test_importar_acreedor_tipo_invalido_usa_otro(self, admin_client, db):
        """Tipo invalido se convierte a 'OTRO'."""
        content = _make_excel(
            ["nombre", "tipo"],
            [["Acreedor Tipo Raro", "DESCONOCIDO"]]
        )
        resp = _post_import(admin_client, "acreedores", content)
        assert resp.status_code == 303

        acr = db.query(models.Acreedor).filter(models.Acreedor.nombre == "Acreedor Tipo Raro").first()
        assert acr is not None
        assert acr.tipo == "OTRO"

    def test_importar_acreedor_duplicado_omitido(self, admin_client, db, sample_acreedor):
        content = _make_excel(
            ["nombre", "tipo"],
            [[sample_acreedor.nombre, "BANCO"]]
        )
        resp = _post_import(admin_client, "acreedores", content)
        assert resp.status_code == 303

        count = db.query(models.Acreedor).filter(
            models.Acreedor.nombre == sample_acreedor.nombre
        ).count()
        assert count == 1


# ── Importar Deudas ──────────────────────────────────────────────────────────

class TestImportarDeudas:
    def test_importar_deuda_simple(self, admin_client, db):
        content = _make_excel(
            ["concepto", "acreedor_nombre", "acreedor_tipo", "monto_total", "monto_pagado", "fecha_deuda", "fecha_vencimiento"],
            [["Deuda Importada", "Acreedor Test", "BANCO", 500000, 0, "2026-01-01", "2026-06-01"]]
        )
        resp = _post_import(admin_client, "deudas", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        deuda = db.query(models.Deuda).filter(models.Deuda.concepto == "Deuda Importada").first()
        assert deuda is not None
        assert deuda.monto_total == 500000
        assert deuda.estado == "PENDIENTE"

    def test_importar_deuda_sin_columnas_requeridas(self, admin_client):
        content = _make_excel(
            ["concepto", "monto_total"],
            [["Deuda sin acreedor", 100000]]
        )
        resp = _post_import(admin_client, "deudas", content)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_importar_deuda_estado_parcial(self, admin_client, db):
        content = _make_excel(
            ["concepto", "acreedor_nombre", "acreedor_tipo", "monto_total", "monto_pagado"],
            [["Deuda Parcial", "Acr Test", "OTRO", 100000, 50000]]
        )
        resp = _post_import(admin_client, "deudas", content)
        assert resp.status_code == 303

        deuda = db.query(models.Deuda).filter(models.Deuda.concepto == "Deuda Parcial").first()
        assert deuda is not None
        assert deuda.estado == "PARCIAL"

    def test_importar_deuda_monto_pagado_mayor_total(self, admin_client, db):
        """Si monto_pagado > monto_total, se limita a monto_total."""
        content = _make_excel(
            ["concepto", "acreedor_nombre", "acreedor_tipo", "monto_total", "monto_pagado"],
            [["Deuda Exceso", "Acr Test", "OTRO", 100000, 999999]]
        )
        resp = _post_import(admin_client, "deudas", content)
        assert resp.status_code == 303

        deuda = db.query(models.Deuda).filter(models.Deuda.concepto == "Deuda Exceso").first()
        assert deuda is not None
        assert deuda.monto_pagado == 100000
        assert deuda.estado == "PAGADO"

    def test_importar_deuda_con_acreedor_existente(self, admin_client, db, sample_acreedor):
        """Si el acreedor existe en BD, se linkea por acreedor_id."""
        content = _make_excel(
            ["concepto", "acreedor_nombre", "acreedor_tipo", "monto_total"],
            [["Deuda Acr Existente", sample_acreedor.nombre, "PROVEEDOR", 200000]]
        )
        resp = _post_import(admin_client, "deudas", content)
        assert resp.status_code == 303

        deuda = db.query(models.Deuda).filter(models.Deuda.concepto == "Deuda Acr Existente").first()
        assert deuda is not None
        assert deuda.acreedor_id == sample_acreedor.id


# ── Importar Facturas ────────────────────────────────────────────────────────

class TestImportarFacturas:
    def test_importar_factura_simple(self, admin_client, db):
        content = _make_excel(
            ["numero_factura", "cliente_nombre", "cliente_documento", "concepto", "monto_total",
             "monto_cobrado", "fecha_emision", "fecha_vencimiento"],
            [["FAC-IMP-001", "Cliente Factura", "CC-001", "Servicio web", 500000,
              0, "2026-01-15", "2026-02-15"]]
        )
        resp = _post_import(admin_client, "facturas", content)
        assert resp.status_code == 303
        assert "msg" in resp.headers["location"].lower()

        fac = db.query(models.Factura).filter(models.Factura.numero_factura == "FAC-IMP-001").first()
        assert fac is not None
        assert fac.cliente_nombre == "Cliente Factura"
        assert fac.estado == "PENDIENTE"

    def test_importar_factura_sin_columnas_requeridas(self, admin_client):
        content = _make_excel(
            ["numero_factura", "monto_total"],
            [["FAC-001", 100000]]
        )
        resp = _post_import(admin_client, "facturas", content)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_importar_factura_duplicada_omitida(self, admin_client, db, sample_factura):
        content = _make_excel(
            ["numero_factura", "cliente_nombre", "concepto", "monto_total"],
            [[sample_factura.numero_factura, "Otro Cliente", "Otro concepto", 200000]]
        )
        resp = _post_import(admin_client, "facturas", content)
        assert resp.status_code == 303

        count = db.query(models.Factura).filter(
            models.Factura.numero_factura == sample_factura.numero_factura
        ).count()
        assert count == 1

    def test_importar_factura_sin_numero_genera_automatico(self, admin_client, db):
        """Sin numero_factura, se genera uno automaticamente."""
        content = _make_excel(
            ["cliente_nombre", "concepto", "monto_total"],
            [["Cliente Auto", "Concepto Auto", 150000]]
        )
        resp = _post_import(admin_client, "facturas", content)
        assert resp.status_code == 303

        fac = db.query(models.Factura).filter(models.Factura.cliente_nombre == "Cliente Auto").first()
        assert fac is not None
        assert fac.numero_factura is not None
        assert fac.numero_factura.startswith("FAC-")


# ── Funciones auxiliares (_parse_date, _col_index, etc.) ─────────────────────

class TestFuncionesAuxiliares:
    def test_parse_date_formato_iso(self):
        from routers.importar import _parse_date
        result = _parse_date("2026-03-15")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 15

    def test_parse_date_formato_slash(self):
        from routers.importar import _parse_date
        result = _parse_date("15/03/2026")
        assert result is not None
        assert result.day == 15

    def test_parse_date_invalida_retorna_none(self):
        from routers.importar import _parse_date
        result = _parse_date("fecha-invalida")
        assert result is None

    def test_col_index_encontrado(self):
        from routers.importar import _col_index
        headers = ["nombre", "codigo", "precio"]
        assert _col_index(headers, "codigo") == 1

    def test_col_index_no_encontrado(self):
        from routers.importar import _col_index
        headers = ["nombre", "codigo"]
        assert _col_index(headers, "descripcion") is None

    def test_cell_str_normal(self):
        from routers.importar import _cell_str
        row = ("valor", 123, None)
        assert _cell_str(row, 0) == "valor"
        assert _cell_str(row, 2) == ""

    def test_cell_float_normal(self):
        from routers.importar import _cell_float
        row = (1000,)
        assert _cell_float(row, 0) == 1000.0

    def test_cell_float_invalido_retorna_default(self):
        from routers.importar import _cell_float
        row = ("no_es_numero",)
        assert _cell_float(row, 0) == 0.0
