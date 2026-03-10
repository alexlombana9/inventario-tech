from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    productos = relationship("Producto", back_populates="categoria")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    contacto = Column(String(100), default="")
    telefono = Column(String(50), default="")
    email = Column(String(100), default="")
    direccion = Column(Text, default="")
    nit_ruc = Column(String(50), default="")
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    productos = relationship("Producto", back_populates="proveedor_principal")
    movimientos = relationship("MovimientoInventario", back_populates="proveedor")
    deudas = relationship("Deuda", back_populates="proveedor")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    precio_costo = Column(Float, default=0.0)
    precio_venta = Column(Float, default=0.0)
    stock_actual = Column(Float, default=0.0)
    stock_minimo = Column(Float, default=0.0)
    unidad_medida = Column(String(20), default="UND")
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    categoria = relationship("Categoria", back_populates="productos")
    proveedor_principal = relationship("Proveedor", back_populates="productos")
    movimientos = relationship("MovimientoInventario", back_populates="producto")

    @property
    def margen(self):
        if self.precio_costo > 0:
            return round(((self.precio_venta - self.precio_costo) / self.precio_costo) * 100, 1)
        return 0.0

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # ENTRADA, SALIDA, AJUSTE
    cantidad = Column(Float, nullable=False)
    stock_anterior = Column(Float, nullable=False)
    stock_resultante = Column(Float, nullable=False)
    precio_unitario = Column(Float, default=0.0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    numero_referencia = Column(String(100), default="")
    observaciones = Column(Text, default="")
    fecha = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    producto = relationship("Producto", back_populates="movimientos")
    proveedor = relationship("Proveedor", back_populates="movimientos")


# ─────────────────────────────────────────────
#  CUENTAS POR PAGAR — Deudas con proveedores
# ─────────────────────────────────────────────

class Deuda(Base):
    __tablename__ = "deudas"

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String(300), nullable=False)
    acreedor_nombre = Column(String(200), nullable=False)   # a quién se le debe
    acreedor_tipo = Column(String(20), default="OTRO")      # PROVEEDOR | LOCAL | OTRO
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    monto_total = Column(Float, nullable=False)
    monto_pagado = Column(Float, default=0.0)
    fecha_deuda = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime, nullable=True)
    estado = Column(String(20), default="PENDIENTE")        # PENDIENTE | PARCIAL | PAGADO
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    proveedor = relationship("Proveedor", back_populates="deudas")
    pagos = relationship("PagoDeuda", back_populates="deuda", cascade="all, delete-orphan")

    @property
    def monto_pendiente(self):
        return max(0.0, self.monto_total - self.monto_pagado)

    @property
    def porcentaje_pagado(self):
        if self.monto_total > 0:
            return min(100, round((self.monto_pagado / self.monto_total) * 100, 1))
        return 0.0

    @property
    def esta_vencida(self):
        if self.estado == "PAGADO":
            return False
        if self.fecha_vencimiento:
            return datetime.now() > self.fecha_vencimiento
        return False


class PagoDeuda(Base):
    __tablename__ = "pagos_deuda"

    id = Column(Integer, primary_key=True, index=True)
    deuda_id = Column(Integer, ForeignKey("deudas.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(DateTime, default=datetime.now)
    metodo_pago = Column(String(50), default="EFECTIVO")    # EFECTIVO | TRANSFERENCIA | TARJETA | CHEQUE
    comprobante = Column(String(100), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    deuda = relationship("Deuda", back_populates="pagos")


# ─────────────────────────────────────────────
#  CUENTAS POR COBRAR — Facturas pendientes
# ─────────────────────────────────────────────

class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    numero_factura = Column(String(100), nullable=False, unique=True)
    cliente_nombre = Column(String(200), nullable=False)
    cliente_documento = Column(String(50), default="")
    cliente_telefono = Column(String(50), default="")
    cliente_email = Column(String(100), default="")
    concepto = Column(Text, nullable=False)
    monto_total = Column(Float, nullable=False)
    monto_cobrado = Column(Float, default=0.0)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime, nullable=True)
    estado = Column(String(20), default="PENDIENTE")        # PENDIENTE | PARCIAL | PAGADO
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    cobros = relationship("PagoFactura", back_populates="factura", cascade="all, delete-orphan")

    @property
    def monto_pendiente(self):
        return max(0.0, self.monto_total - self.monto_cobrado)

    @property
    def porcentaje_cobrado(self):
        if self.monto_total > 0:
            return min(100, round((self.monto_cobrado / self.monto_total) * 100, 1))
        return 0.0

    @property
    def esta_vencida(self):
        if self.estado == "PAGADO":
            return False
        if self.fecha_vencimiento:
            return datetime.now() > self.fecha_vencimiento
        return False


class PagoFactura(Base):
    __tablename__ = "cobros_factura"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_cobro = Column(DateTime, default=datetime.now)
    metodo_pago = Column(String(50), default="EFECTIVO")
    comprobante = Column(String(100), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    factura = relationship("Factura", back_populates="cobros")
