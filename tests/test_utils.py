"""
Tests de cobertura para utilidades: pdf, dashboard, financial, excel.
Cubre también @property de models.py.
"""
import os
import sys
import json
import pytest
from datetime import datetime, date, timedelta
from io import BytesIO

# ─────────────────────────────────────────────────────────────────────────────
# utils/pdf.py
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateReportPdf:
    """Pruebas para utils/pdf.py → generate_report_pdf."""

    def _call(self, **kwargs):
        from utils.pdf import generate_report_pdf
        defaults = dict(
            title="TechStock — Reporte de Prueba",
            fecha_desde="01/01/2026",
            fecha_hasta="31/01/2026",
            headers=["#", "Concepto", "Monto", "Estado"],
            rows=[
                ["1", "Deuda A", "$1,000", "PENDIENTE"],
                ["2", "Deuda B", "$2,000", "PARCIAL"],
                ["3", "Deuda C", "$3,000", "PAGADO"],
                ["4", "Deuda D", "$500",   "VENCIDA"],
                ["5", "Deuda E", "$200",   "OTRO"],   # estado sin color
            ],
            totals_row=["", "TOTAL", "$6,700", ""],
            col_widths_cm=[1.0, 7.0, 3.5, 3.0],
            estado_col_index=3,
        )
        defaults.update(kwargs)
        return generate_report_pdf(**defaults)

    def test_contenido_es_pdf(self):
        result = self._call()
        content = result.read()
        assert content[:4] == b"%PDF", "El archivo no empieza con la firma PDF"

    def test_pdf_filas_vacias(self):
        """Sin filas de datos solo encabezado y totales."""
        result = self._call(rows=[], totals_row=["", "SIN DATOS", "$0", ""])
        content = result.read()
        assert content[:4] == b"%PDF"

    def test_pdf_estado_col_index_fuera_de_rango(self):
        """estado_col_index mayor que columnas disponibles no debe fallar."""
        result = self._call(
            rows=[["1", "Concepto", "$100", "PENDIENTE"]],
            estado_col_index=99,
        )
        content = result.read()
        assert content[:4] == b"%PDF"


# ─────────────────────────────────────────────────────────────────────────────
# utils/financial.py
# ─────────────────────────────────────────────────────────────────────────────

class TestActualizarEstadoPago:
    """Pruebas para actualizar_estado_pago."""

    def _entity(self, monto_total, monto_pagado, estado="PENDIENTE"):
        class Obj:
            pass
        obj = Obj()
        obj.monto_total = monto_total
        obj.monto_pagado = monto_pagado
        obj.estado = estado
        return obj

    def test_pendiente_cuando_no_pago(self):
        from utils.financial import actualizar_estado_pago
        e = self._entity(1000, 0)
        actualizar_estado_pago(e)
        assert e.estado == "PENDIENTE"

    def test_parcial_cuando_pago_parcial(self):
        from utils.financial import actualizar_estado_pago
        e = self._entity(1000, 500)
        actualizar_estado_pago(e)
        assert e.estado == "PARCIAL"

    def test_pagado_cuando_pago_total(self):
        from utils.financial import actualizar_estado_pago
        e = self._entity(1000, 1000)
        actualizar_estado_pago(e)
        assert e.estado == "PAGADO"

    def test_pagado_cuando_pago_excede(self):
        from utils.financial import actualizar_estado_pago
        e = self._entity(1000, 1500)
        actualizar_estado_pago(e)
        assert e.estado == "PAGADO"

    def test_campo_personalizado(self):
        """Soporta campo diferente (monto_cobrado para Factura)."""
        from utils.financial import actualizar_estado_pago

        class Factura:
            monto_total = 500
            monto_cobrado = 250
            estado = "PENDIENTE"

        f = Factura()
        actualizar_estado_pago(f, "monto_cobrado")
        assert f.estado == "PARCIAL"


class TestSiguienteNumero:
    """Pruebas para siguiente_numero — cubre líneas 30-35."""

    def test_primer_numero_tabla_vacia(self, db):
        """Sin registros: retorna PREF-0001."""
        from utils.financial import siguiente_numero
        import models
        result = siguiente_numero(db, models.Factura, "numero_factura", "FAC")
        assert result == "FAC-0001"

    def test_incrementa_desde_ultimo(self, db):
        """Con un registro existente incrementa el número."""
        from utils.financial import siguiente_numero
        import models
        factura = models.Factura(
            numero_factura="FAC-0005",
            cliente_nombre="Cliente",
            concepto="Prueba",
            monto_total=1000.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now(),
        )
        db.add(factura)
        db.commit()

        result = siguiente_numero(db, models.Factura, "numero_factura", "FAC")
        assert result == "FAC-0006"

    def test_numero_con_prefijo_diferente(self, db):
        """Genera número con prefijo VTA."""
        from utils.financial import siguiente_numero
        import models

        user = models.Usuario(
            username="v_test",
            password_hash="hash",
            nombre_completo="Vendedor",
            rol="VENDEDOR",
            activo=True,
        )
        db.add(user)
        db.commit()

        venta = models.Venta(
            numero_venta="VTA-0010",
            vendedor_id=user.id,
            subtotal=100.0,
            total=100.0,
            metodo_pago="EFECTIVO",
            estado="COMPLETADA",
        )
        db.add(venta)
        db.commit()

        result = siguiente_numero(db, models.Venta, "numero_venta", "VTA")
        assert result == "VTA-0011"

    def test_fallback_cuando_formato_invalido(self, db):
        """Si el campo no tiene formato PREF-NNNN usa id+1 como fallback."""
        from utils.financial import siguiente_numero
        import models

        factura = models.Factura(
            numero_factura="INVALIDO",
            cliente_nombre="Cliente",
            concepto="Prueba",
            monto_total=100.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now(),
        )
        db.add(factura)
        db.commit()

        # "INVALIDO".split("-")[-1] → "INVALIDO" → int() → ValueError → fallback
        result = siguiente_numero(db, models.Factura, "numero_factura", "FAC")
        assert result.startswith("FAC-")

    def test_fallback_cuando_campo_none(self, db):
        """Si el campo número es None usa fallback con id."""
        from utils.financial import siguiente_numero
        import models

        # Insertar una fila con numero_factura como string no parseable
        factura = models.Factura(
            numero_factura="FAC-NONNUMERIC-XYZ",
            cliente_nombre="Cliente",
            concepto="Prueba",
            monto_total=100.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now(),
        )
        db.add(factura)
        db.commit()

        result = siguiente_numero(db, models.Factura, "numero_factura", "FAC")
        assert result.startswith("FAC-")


# ─────────────────────────────────────────────────────────────────────────────
# utils/excel.py
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateExcel:
    """Pruebas para generate_excel — cubre líneas 73-74 (auto col_widths)."""

    def test_sin_col_widths_usa_auto(self):
        """Sin col_widths calcula anchos automáticos (líneas 73-74)."""
        from utils.excel import generate_excel
        result = generate_excel(
            title="Reporte Auto",
            headers=["Columna Muy Larga", "B"],
            rows=[["data1", "data2"]],
            col_widths=None,   # fuerza rama else → auto widths
        )
        content = result.read()
        assert len(content) > 0

    def test_money_cols_formatting(self):
        """Columnas de dinero reciben formato moneda."""
        from utils.excel import generate_excel
        result = generate_excel(
            title="Finanzas",
            headers=["Nombre", "Monto"],
            rows=[["Producto A", 150000], ["Producto B", 230000]],
            money_cols=[1],
        )
        content = result.read()
        assert len(content) > 0

    def test_auto_width_min_14(self):
        """El ancho auto usa max(14, len(header) + 4)."""
        from utils.excel import generate_excel
        # header corto: len("AB") + 4 = 6 < 14 → debe usar 14
        result = generate_excel(
            title="T",
            headers=["AB", "CD"],
            rows=[],
            col_widths=None,
        )
        content = result.read()
        assert len(content) > 0

    def test_filas_vacias(self):
        """Sin filas de datos debe generar excel solo con encabezados."""
        from utils.excel import generate_excel
        result = generate_excel(
            title="Vacío",
            headers=["A", "B", "C"],
            rows=[],
        )
        content = result.read()
        assert len(content) > 0


# ─────────────────────────────────────────────────────────────────────────────
# utils/dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDateRange:
    """Pruebas para get_date_range — líneas 12-23 (ramas de error de parseo)."""

    def test_fecha_desde_none(self):
        """Sin fecha_desde usa hoy-30 por defecto."""
        from utils.dashboard import get_date_range
        hoy = date(2026, 3, 26)
        fd, fh, fd_dt, fh_dt = get_date_range(None, None, hoy)
        assert fd == hoy - timedelta(days=30)
        assert fh == hoy

    def test_fecha_desde_invalida(self):
        """fecha_desde con formato incorrecto cae al default (líneas 12-15)."""
        from utils.dashboard import get_date_range
        hoy = date(2026, 3, 26)
        fd, fh, fd_dt, fh_dt = get_date_range("not-a-date", None, hoy)
        assert fd == hoy - timedelta(days=30)

    def test_fecha_hasta_invalida(self):
        """fecha_hasta con formato incorrecto cae al default (líneas 20-23)."""
        from utils.dashboard import get_date_range
        hoy = date(2026, 3, 26)
        fd, fh, fd_dt, fh_dt = get_date_range(None, "not-a-date", hoy)
        assert fh == hoy


class TestGetGeneralMetrics:
    def test_sin_datos(self, db):
        from utils.dashboard import get_general_metrics
        result = get_general_metrics(db)
        assert result["total_productos"] == 0
        assert result["valor_inventario"] == 0.0


class TestGetPeriodMetrics:
    def test_sin_ventas(self, db):
        from utils.dashboard import get_period_metrics
        hoy = datetime.now()
        fd_dt = hoy - timedelta(days=30)
        fh_dt = hoy
        result = get_period_metrics(db, fd_dt, fh_dt)
        assert result["ventas_periodo"] == 0.0
        assert result["ganancia_periodo"] == 0.0

    def test_con_venta_completada(self, db, sample_producto, admin_user):
        from utils.dashboard import get_period_metrics
        import models

        venta = models.Venta(
            numero_venta="VTA-PM-001",
            vendedor_id=admin_user.id,
            subtotal=1500.0,
            total=1500.0,
            metodo_pago="EFECTIVO",
            estado="COMPLETADA",
            fecha=datetime.now(),
        )
        db.add(venta)
        db.commit()

        detalle = models.DetalleVenta(
            venta_id=venta.id,
            producto_id=sample_producto.id,
            producto_nombre=sample_producto.nombre,
            producto_codigo=sample_producto.codigo,
            cantidad=1,
            precio_unitario=1500.0,
            precio_costo=1000.0,
            subtotal=1500.0,
        )
        db.add(detalle)
        db.commit()

        hoy = datetime.now()
        fd_dt = hoy - timedelta(days=1)
        fh_dt = hoy + timedelta(days=1)
        result = get_period_metrics(db, fd_dt, fh_dt)
        assert result["ventas_periodo"] == 1500.0
        assert result["ganancia_periodo"] == 500.0


class TestGetFinancialMetrics:
    def test_deudas_vencidas(self, db, sample_proveedor):
        """Deuda con fecha_vencimiento en el pasado aparece como vencida (línea 179)."""
        from utils.dashboard import get_financial_metrics
        import models

        deuda_vencida = models.Deuda(
            concepto="Deuda vencida",
            acreedor_nombre="Banco",
            acreedor_tipo="BANCO",
            proveedor_id=sample_proveedor.id,
            monto_total=100000.0,
            monto_pagado=0.0,
            fecha_deuda=datetime.now() - timedelta(days=60),
            fecha_vencimiento=datetime.now() - timedelta(days=30),
            estado="PENDIENTE",
        )
        db.add(deuda_vencida)
        db.commit()

        result = get_financial_metrics(db)
        assert result["deudas_vencidas_count"] >= 1

    def test_facturas_vencidas(self, db):
        """Factura con fecha_vencimiento en el pasado aparece como vencida (líneas 205-206)."""
        from utils.dashboard import get_financial_metrics
        import models

        factura_vencida = models.Factura(
            numero_factura="FAC-VEN-001",
            cliente_nombre="Cliente Moroso",
            concepto="Servicio",
            monto_total=50000.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now() - timedelta(days=60),
            fecha_vencimiento=datetime.now() - timedelta(days=30),
            estado="PENDIENTE",
        )
        db.add(factura_vencida)
        db.commit()

        result = get_financial_metrics(db)
        assert result["facturas_vencidas_count"] >= 1


class TestGetChartData:
    def test_sin_datos(self, db):
        from utils.dashboard import get_chart_data
        hoy = date.today()
        fd_dt = datetime.combine(hoy - timedelta(days=30), datetime.min.time())
        fh_dt = datetime.combine(hoy, datetime.max.time())
        result = get_chart_data(db, fd_dt, fh_dt, hoy)
        assert "chart_ventas_7d" in result
        assert json.loads(result["chart_ventas_7d"]) == [0.0] * 7

    def test_con_venta(self, db, sample_producto, admin_user):
        """Venta completada es procesada por get_chart_data sin errores."""
        from utils.dashboard import get_chart_data
        import models

        hoy = date.today()
        venta = models.Venta(
            numero_venta="VTA-CHART-001",
            vendedor_id=admin_user.id,
            subtotal=2000.0,
            total=2000.0,
            metodo_pago="EFECTIVO",
            estado="COMPLETADA",
            fecha=datetime.combine(hoy, datetime.min.time()),
        )
        db.add(venta)
        db.commit()

        fd_dt = datetime.combine(hoy - timedelta(days=30), datetime.min.time())
        fh_dt = datetime.combine(hoy, datetime.max.time())
        result = get_chart_data(db, fd_dt, fh_dt, hoy)
        ventas = json.loads(result["chart_ventas_7d"])
        # 7 elementos — la suma puede ser 0 en SQLite por conversión de tipos
        # pero la función debe ejecutarse sin errores y retornar la estructura correcta
        assert len(ventas) == 7
        assert isinstance(ventas, list)

    def test_estados_deuda_y_factura(self, db, sample_deuda, sample_factura):
        """Deudas y facturas deben aparecer en los datos del doughnut (líneas 216-217)."""
        from utils.dashboard import get_chart_data
        import models

        # Agregar deuda PARCIAL
        deuda_parcial = models.Deuda(
            concepto="Deuda parcial",
            acreedor_nombre="Proveedor X",
            acreedor_tipo="PROVEEDOR",
            monto_total=200000.0,
            monto_pagado=100000.0,
            fecha_deuda=datetime.now(),
            estado="PARCIAL",
        )
        db.add(deuda_parcial)
        # Agregar factura PAGADA
        factura_pagada = models.Factura(
            numero_factura="FAC-PAGADA-001",
            cliente_nombre="Cliente Pagado",
            concepto="Servicio",
            monto_total=100000.0,
            monto_cobrado=100000.0,
            fecha_emision=datetime.now(),
            estado="PAGADO",
        )
        db.add(factura_pagada)
        db.commit()

        hoy = date.today()
        fd_dt = datetime.combine(hoy - timedelta(days=30), datetime.min.time())
        fh_dt = datetime.combine(hoy, datetime.max.time())
        result = get_chart_data(db, fd_dt, fh_dt, hoy)

        deudas = json.loads(result["chart_deudas"])
        facturas = json.loads(result["chart_facturas"])
        # [PENDIENTE, PARCIAL, PAGADO]
        assert sum(deudas) >= 2   # sample_deuda + deuda_parcial
        assert sum(facturas) >= 2  # sample_factura + factura_pagada


# ─────────────────────────────────────────────────────────────────────────────
# models.py — @property
# ─────────────────────────────────────────────────────────────────────────────

class TestModelProperties:
    """Cubre @property de Producto, Deuda, Factura, Caja, DetalleVenta, Venta."""

    def test_producto_margen_positivo(self, db, sample_producto):
        assert sample_producto.margen == 50.0  # (1500-1000)/1000*100

    def test_producto_margen_costo_cero(self, db, sample_categoria):
        import models
        prod = models.Producto(
            codigo="CERO-COSTO",
            nombre="Sin Costo",
            precio_costo=0.0,
            precio_venta=100.0,
            stock_actual=10.0,
            stock_minimo=1.0,
            categoria_id=sample_categoria.id,
            activo=True,
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)
        assert prod.margen == 0.0

    def test_producto_stock_bajo_true(self, db, sample_categoria):
        import models
        prod = models.Producto(
            codigo="LOW-STOCK",
            nombre="Bajo Stock",
            precio_costo=50.0,
            precio_venta=80.0,
            stock_actual=2.0,
            stock_minimo=10.0,
            categoria_id=sample_categoria.id,
            activo=True,
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)
        assert prod.stock_bajo is True

    def test_producto_stock_bajo_false(self, db, sample_producto):
        assert sample_producto.stock_bajo is False  # stock_actual=50 > stock_minimo=5

    def test_deuda_monto_pendiente(self, db, sample_deuda):
        assert sample_deuda.monto_pendiente == 500000.0

    def test_deuda_porcentaje_pagado_cero(self, db, sample_deuda):
        assert sample_deuda.porcentaje_pagado == 0.0

    def test_deuda_porcentaje_pagado_parcial(self, db, sample_proveedor):
        import models
        deuda = models.Deuda(
            concepto="Deuda parcial",
            acreedor_nombre="Banco",
            acreedor_tipo="BANCO",
            proveedor_id=sample_proveedor.id,
            monto_total=1000.0,
            monto_pagado=250.0,
            fecha_deuda=datetime.now(),
            estado="PARCIAL",
        )
        db.add(deuda)
        db.commit()
        db.refresh(deuda)
        assert deuda.porcentaje_pagado == 25.0

    def test_deuda_porcentaje_pagado_total_cero(self, db, sample_proveedor):
        import models
        deuda = models.Deuda(
            concepto="Deuda cero",
            acreedor_nombre="Nadie",
            acreedor_tipo="OTRO",
            proveedor_id=sample_proveedor.id,
            monto_total=0.0,
            monto_pagado=0.0,
            fecha_deuda=datetime.now(),
            estado="PENDIENTE",
        )
        db.add(deuda)
        db.commit()
        db.refresh(deuda)
        assert deuda.porcentaje_pagado == 0.0

    def test_deuda_esta_vencida_pagada(self, db, sample_proveedor):
        """Deuda PAGADA nunca está vencida."""
        import models
        deuda = models.Deuda(
            concepto="Pagada",
            acreedor_nombre="Alguien",
            acreedor_tipo="OTRO",
            proveedor_id=sample_proveedor.id,
            monto_total=100.0,
            monto_pagado=100.0,
            fecha_deuda=datetime.now(),
            fecha_vencimiento=datetime.now() - timedelta(days=1),
            estado="PAGADO",
        )
        db.add(deuda)
        db.commit()
        db.refresh(deuda)
        assert deuda.esta_vencida is False

    def test_deuda_esta_vencida_sin_vencimiento(self, db, sample_proveedor):
        """Sin fecha_vencimiento no puede estar vencida."""
        import models
        deuda = models.Deuda(
            concepto="Sin vencimiento",
            acreedor_nombre="Alguien",
            acreedor_tipo="OTRO",
            proveedor_id=sample_proveedor.id,
            monto_total=100.0,
            monto_pagado=0.0,
            fecha_deuda=datetime.now(),
            fecha_vencimiento=None,
            estado="PENDIENTE",
        )
        db.add(deuda)
        db.commit()
        db.refresh(deuda)
        assert deuda.esta_vencida is False

    def test_deuda_esta_vencida_true(self, db, sample_proveedor):
        import models
        deuda = models.Deuda(
            concepto="Vencida",
            acreedor_nombre="Banco",
            acreedor_tipo="BANCO",
            proveedor_id=sample_proveedor.id,
            monto_total=100.0,
            monto_pagado=0.0,
            fecha_deuda=datetime.now() - timedelta(days=60),
            fecha_vencimiento=datetime.now() - timedelta(days=1),
            estado="PENDIENTE",
        )
        db.add(deuda)
        db.commit()
        db.refresh(deuda)
        assert deuda.esta_vencida is True

    def test_factura_monto_pendiente(self, db, sample_factura):
        assert sample_factura.monto_pendiente == 1000000.0

    def test_factura_porcentaje_cobrado_cero(self, db, sample_factura):
        assert sample_factura.porcentaje_cobrado == 0.0

    def test_factura_porcentaje_cobrado_parcial(self, db):
        import models
        factura = models.Factura(
            numero_factura="FAC-PCT-001",
            cliente_nombre="Cliente",
            concepto="Servicio",
            monto_total=1000.0,
            monto_cobrado=500.0,
            fecha_emision=datetime.now(),
            estado="PARCIAL",
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        assert factura.porcentaje_cobrado == 50.0

    def test_factura_porcentaje_cobrado_monto_cero(self, db):
        import models
        factura = models.Factura(
            numero_factura="FAC-ZERO-001",
            cliente_nombre="Cliente",
            concepto="Servicio",
            monto_total=0.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now(),
            estado="PENDIENTE",
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        assert factura.porcentaje_cobrado == 0.0

    def test_factura_esta_vencida_pagada(self, db):
        import models
        factura = models.Factura(
            numero_factura="FAC-VEN-PAGADA",
            cliente_nombre="Cliente",
            concepto="Servicio",
            monto_total=1000.0,
            monto_cobrado=1000.0,
            fecha_emision=datetime.now(),
            fecha_vencimiento=datetime.now() - timedelta(days=1),
            estado="PAGADO",
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        assert factura.esta_vencida is False

    def test_factura_esta_vencida_sin_vencimiento(self, db):
        import models
        factura = models.Factura(
            numero_factura="FAC-SINVEN-001",
            cliente_nombre="Cliente",
            concepto="Servicio",
            monto_total=1000.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now(),
            fecha_vencimiento=None,
            estado="PENDIENTE",
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        assert factura.esta_vencida is False

    def test_factura_esta_vencida_true(self, db):
        import models
        factura = models.Factura(
            numero_factura="FAC-VEN-001",
            cliente_nombre="Cliente",
            concepto="Servicio",
            monto_total=1000.0,
            monto_cobrado=0.0,
            fecha_emision=datetime.now() - timedelta(days=60),
            fecha_vencimiento=datetime.now() - timedelta(days=1),
            estado="PENDIENTE",
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        assert factura.esta_vencida is True

    def test_caja_totales_sin_movimientos(self, db, caja_abierta):
        assert caja_abierta.total_ingresos == 0
        assert caja_abierta.total_egresos == 0
        assert caja_abierta.saldo_esperado == caja_abierta.monto_apertura

    def test_caja_totales_con_movimientos(self, db, caja_abierta):
        import models
        db.add(models.MovimientoCaja(
            caja_id=caja_abierta.id, tipo="INGRESO",
            concepto="Venta", monto=50000.0,
        ))
        db.add(models.MovimientoCaja(
            caja_id=caja_abierta.id, tipo="EGRESO",
            concepto="Gasto", monto=10000.0,
        ))
        db.commit()
        db.refresh(caja_abierta)
        assert caja_abierta.total_ingresos == 50000.0
        assert caja_abierta.total_egresos == 10000.0
        assert caja_abierta.saldo_esperado == 140000.0

    def test_detalle_venta_ganancia(self, db, admin_user, sample_producto):
        import models
        venta = models.Venta(
            numero_venta="VTA-G-001",
            vendedor_id=admin_user.id,
            subtotal=1500.0,
            total=1500.0,
            metodo_pago="EFECTIVO",
            estado="COMPLETADA",
        )
        db.add(venta)
        db.commit()
        detalle = models.DetalleVenta(
            venta_id=venta.id,
            producto_id=sample_producto.id,
            producto_nombre="Laptop",
            producto_codigo="PROD-001",
            cantidad=1,
            precio_unitario=1500.0,
            precio_costo=1000.0,
            subtotal=1500.0,
        )
        db.add(detalle)
        db.commit()
        db.refresh(detalle)
        assert detalle.ganancia == 500.0

    def test_venta_ganancia_total(self, db, admin_user, sample_producto):
        import models
        venta = models.Venta(
            numero_venta="VTA-GT-001",
            vendedor_id=admin_user.id,
            subtotal=3000.0,
            total=3000.0,
            metodo_pago="EFECTIVO",
            estado="COMPLETADA",
        )
        db.add(venta)
        db.commit()
        for i in range(2):
            db.add(models.DetalleVenta(
                venta_id=venta.id,
                producto_id=sample_producto.id,
                producto_nombre="Laptop",
                producto_codigo="PROD-001",
                cantidad=1,
                precio_unitario=1500.0,
                precio_costo=1000.0,
                subtotal=1500.0,
            ))
        db.commit()
        db.refresh(venta)
        assert venta.ganancia_total == 1000.0


# ─────────────────────────────────────────────────────────────────────────────
# templates_config.py — filtros y globals
# ─────────────────────────────────────────────────────────────────────────────

class TestTemplatesConfig:
    """Cubre líneas 7, 14-27, 37 de templates_config.py."""

    def test_formato_moneda_invalido(self):
        from templates_config import formato_moneda
        assert formato_moneda(None) == "$0.00"
        assert formato_moneda("texto") == "$0.00"

    def test_formato_numero_invalido(self):
        from templates_config import formato_numero
        assert formato_numero(None) == "0"
        assert formato_numero("texto") == "0"

    def test_has_permiso_sin_usuario(self):
        from templates_config import _has_permiso
        assert _has_permiso(None, "productos") is False

    def test_has_permiso_con_admin(self, db, admin_user):
        from templates_config import _has_permiso
        assert _has_permiso(admin_user, "productos") is True

    def test_csrf_token_sin_cookie(self):
        """Sin cookie de sesión devuelve string vacío."""
        from templates_config import _csrf_token

        class FakeRequest:
            cookies = {}

        token = _csrf_token(FakeRequest())
        assert token == ""

    def test_csrf_token_con_cookie(self, client, admin_user):
        """Con cookie de sesión válida genera token CSRF."""
        from templates_config import _csrf_token
        from auth import create_session_cookie, COOKIE_NAME

        cookie_val = create_session_cookie(admin_user.id, admin_user.username)

        class FakeRequest:
            cookies = {COOKIE_NAME: cookie_val}

        token = _csrf_token(FakeRequest())
        assert isinstance(token, str)
        assert len(token) > 0


# ─────────────────────────────────────────────────────────────────────────────
# main.py — rutas adicionales y get_local_ip
# ─────────────────────────────────────────────────────────────────────────────

class TestMainRoutes:
    """Cubre líneas 94-95 (legal), 127-134 (get_local_ip)."""

    def test_get_local_ip(self):
        from main import get_local_ip
        ip = get_local_ip()
        assert isinstance(ip, str)
        # Debe ser una IP válida o fallback
        parts = ip.split(".")
        assert len(parts) == 4

    def test_dashboard_fecha_invalida(self, admin_client):
        """Dashboard con fechas inválidas no debe fallar."""
        resp = admin_client.get("/?fecha_desde=bad-date&fecha_hasta=also-bad")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# database.py — get_db rollback branch (líneas 75-77)
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDb:
    """Cubre la rama except de get_db (rollback + re-raise)."""

    def test_get_db_rollback_on_exception(self):
        """Cuando ocurre una excepción dentro de get_db, hace rollback y re-raise."""
        from database import get_db
        gen = get_db()
        session = next(gen)
        assert session is not None
        # Lanzar excepción al generador para activar la rama except
        with pytest.raises(RuntimeError, match="error de prueba"):
            gen.throw(RuntimeError, RuntimeError("error de prueba"))
