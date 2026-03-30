from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ─────────────────────────────────────────────
#  LOCALES (MULTI-TENANT)
# ─────────────────────────────────────────────

class Local(Base):
    __tablename__ = "locales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    direccion = Column(Text, default="")
    telefono = Column(String(50), default="")
    email = Column(String(100), default="")
    ciudad = Column(String(100), default="")
    responsable = Column(String(200), default="")
    activo = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    usuarios = relationship("Usuario", back_populates="local")
    configuracion = relationship("Configuracion", back_populates="local", uselist=False)

    def __repr__(self):
        return f"<Local(id={self.id}, codigo='{self.codigo}', nombre='{self.nombre}')>"


# ─────────────────────────────────────────────
#  USUARIOS Y AUDITORÍA
# ─────────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(200), nullable=False)
    email = Column(String(100), default="")
    telefono = Column(String(50), default="")
    foto = Column(String(255), default="")
    rol = Column(String(20), nullable=False, default="VENDEDOR")  # SUPERADMIN, ADMIN, VENDEDOR, BODEGUERO
    permisos = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    activo = Column(Boolean, default=True, index=True)
    ultimo_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    local = relationship("Local", back_populates="usuarios")

    def __repr__(self):
        return f"<Usuario(id={self.id}, username='{self.username}', rol='{self.rol}')>"


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entidad_created", "entidad", "created_at"),
        Index("ix_audit_log_local_created", "local_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    usuario_nombre = Column(String(200), default="")
    accion = Column(String(50), nullable=False, index=True)
    entidad = Column(String(50), default="")
    entidad_id = Column(Integer, nullable=True)
    detalle = Column(Text, default="")
    ip_address = Column(String(45), default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, accion='{self.accion}', entidad='{self.entidad}')>"


class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (
        UniqueConstraint("nombre", "local_id", name="uq_categorias_nombre_local"),
        Index("ix_categorias_local_activo", "local_id", "activo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, default="")
    activo = Column(Boolean, default=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    productos = relationship("Producto", back_populates="categoria")

    def __repr__(self):
        return f"<Categoria(id={self.id}, nombre='{self.nombre}')>"


class Proveedor(Base):
    __tablename__ = "proveedores"
    __table_args__ = (
        Index("ix_proveedores_local_activo", "local_id", "activo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    contacto = Column(String(100), default="")
    telefono = Column(String(50), default="")
    email = Column(String(100), default="")
    direccion = Column(Text, default="")
    nit_ruc = Column(String(50), default="")
    activo = Column(Boolean, default=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    productos = relationship("Producto", back_populates="proveedor_principal")
    movimientos = relationship("MovimientoInventario", back_populates="proveedor")
    deudas = relationship("Deuda", back_populates="proveedor")

    def __repr__(self):
        return f"<Proveedor(id={self.id}, nombre='{self.nombre}')>"


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        Index("ix_productos_activo_stock", "activo", "stock_actual"),
        Index("ix_productos_local_activo", "local_id", "activo"),
        Index("ix_productos_local_activo_stock", "local_id", "activo", "stock_actual"),
        UniqueConstraint("codigo", "local_id", name="uq_productos_codigo_local"),
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, index=True)
    referencia = Column(String(100), default="")
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    precio_costo = Column(Float, default=0.0)
    precio_venta = Column(Float, default=0.0)
    precio_venta_minimo = Column(Float, default=0.0)
    stock_actual = Column(Float, default=0.0)
    stock_minimo = Column(Float, default=0.0)
    unidad_medida = Column(String(20), default="UND")
    activo = Column(Boolean, default=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
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

    def __repr__(self):
        return f"<Producto(id={self.id}, codigo='{self.codigo}', nombre='{self.nombre}')>"


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        Index("ix_mov_inv_fecha_tipo", "fecha", "tipo"),
        Index("ix_mov_inv_local_fecha", "local_id", "fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)
    cantidad = Column(Float, nullable=False)
    stock_anterior = Column(Float, nullable=False)
    stock_resultante = Column(Float, nullable=False)
    precio_unitario = Column(Float, default=0.0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    numero_referencia = Column(String(100), default="")
    observaciones = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    fecha = Column(DateTime, default=datetime.now, index=True)
    created_at = Column(DateTime, default=datetime.now)

    producto = relationship("Producto", back_populates="movimientos")
    proveedor = relationship("Proveedor", back_populates="movimientos")

    def __repr__(self):
        return f"<MovimientoInventario(id={self.id}, tipo='{self.tipo}', producto_id={self.producto_id})>"


# ─────────────────────────────────────────────
#  ACREEDORES
# ─────────────────────────────────────────────

class Acreedor(Base):
    __tablename__ = "acreedores"
    __table_args__ = (
        Index("ix_acreedores_local_activo", "local_id", "activo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    empresa = Column(String(200), default="")
    tipo = Column(String(20), default="OTRO")
    documento = Column(String(50), default="")
    telefono = Column(String(50), default="")
    email = Column(String(100), default="")
    direccion = Column(Text, default="")
    notas = Column(Text, default="")
    activo = Column(Boolean, default=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    deudas = relationship("Deuda", back_populates="acreedor")

    def __repr__(self):
        return f"<Acreedor(id={self.id}, nombre='{self.nombre}', tipo='{self.tipo}')>"


# ─────────────────────────────────────────────
#  CUENTAS POR PAGAR — Deudas con proveedores
# ─────────────────────────────────────────────

class Deuda(Base):
    __tablename__ = "deudas"
    __table_args__ = (
        Index("ix_deudas_estado_vencimiento", "estado", "fecha_vencimiento"),
        Index("ix_deudas_local_estado", "local_id", "estado"),
    )

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String(300), nullable=False)
    acreedor_nombre = Column(String(200), nullable=False)
    acreedor_empresa = Column(String(200), default="")
    acreedor_tipo = Column(String(20), default="OTRO")
    acreedor_id = Column(Integer, ForeignKey("acreedores.id"), nullable=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    monto_total = Column(Float, nullable=False)
    monto_pagado = Column(Float, default=0.0)
    fecha_deuda = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime, nullable=True)
    estado = Column(String(20), default="PENDIENTE", index=True)
    notas = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    proveedor = relationship("Proveedor", back_populates="deudas")
    acreedor = relationship("Acreedor", back_populates="deudas")
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

    def __repr__(self):
        return f"<Deuda(id={self.id}, concepto='{self.concepto[:30]}', estado='{self.estado}')>"


class PagoDeuda(Base):
    __tablename__ = "pagos_deuda"

    id = Column(Integer, primary_key=True, index=True)
    deuda_id = Column(Integer, ForeignKey("deudas.id"), nullable=False, index=True)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(DateTime, default=datetime.now)
    metodo_pago = Column(String(50), default="EFECTIVO")
    comprobante = Column(String(100), default="")
    notas = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    deuda = relationship("Deuda", back_populates="pagos")

    def __repr__(self):
        return f"<PagoDeuda(id={self.id}, deuda_id={self.deuda_id}, monto={self.monto})>"


# ─────────────────────────────────────────────
#  CUENTAS POR COBRAR — Facturas pendientes
# ─────────────────────────────────────────────

class Factura(Base):
    __tablename__ = "facturas"
    __table_args__ = (
        Index("ix_facturas_estado_vencimiento", "estado", "fecha_vencimiento"),
        Index("ix_facturas_local_estado", "local_id", "estado"),
        UniqueConstraint("numero_factura", "local_id", name="uq_facturas_numero_local"),
    )

    id = Column(Integer, primary_key=True, index=True)
    numero_factura = Column(String(100), nullable=False)
    cliente_nombre = Column(String(200), nullable=False)
    cliente_empresa = Column(String(200), default="")
    cliente_documento = Column(String(50), default="")
    cliente_telefono = Column(String(50), default="")
    cliente_email = Column(String(100), default="")
    concepto = Column(Text, nullable=False)
    monto_total = Column(Float, nullable=False)
    monto_cobrado = Column(Float, default=0.0)
    fecha_emision = Column(DateTime, default=datetime.now, index=True)
    fecha_vencimiento = Column(DateTime, nullable=True)
    estado = Column(String(20), default="PENDIENTE", index=True)
    notas = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
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

    def __repr__(self):
        return f"<Factura(id={self.id}, numero='{self.numero_factura}', estado='{self.estado}')>"


class PagoFactura(Base):
    __tablename__ = "cobros_factura"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False, index=True)
    monto = Column(Float, nullable=False)
    fecha_cobro = Column(DateTime, default=datetime.now)
    metodo_pago = Column(String(50), default="EFECTIVO")
    comprobante = Column(String(100), default="")
    notas = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    factura = relationship("Factura", back_populates="cobros")

    def __repr__(self):
        return f"<PagoFactura(id={self.id}, factura_id={self.factura_id}, monto={self.monto})>"


# ─────────────────────────────────────────────
#  GASTOS DEL NEGOCIO
# ─────────────────────────────────────────────

class Gasto(Base):
    __tablename__ = "gastos"
    __table_args__ = (
        Index("ix_gastos_activo_fecha", "activo", "fecha"),
        Index("ix_gastos_local_activo_fecha", "local_id", "activo", "fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String(300), nullable=False)
    tipo = Column(String(20), default="DIRECTO")
    categoria_gasto = Column(String(100), default="")
    monto = Column(Float, nullable=False)
    fecha = Column(DateTime, default=datetime.now, index=True)
    metodo_pago = Column(String(50), default="EFECTIVO")
    comprobante = Column(String(100), default="")
    notas = Column(Text, default="")
    activo = Column(Boolean, default=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Gasto(id={self.id}, concepto='{self.concepto[:30]}', monto={self.monto})>"


# ─────────────────────────────────────────────
#  CONFIGURACIÓN DEL NEGOCIO (una por local)
# ─────────────────────────────────────────────

class Configuracion(Base):
    __tablename__ = "configuracion"

    id = Column(Integer, primary_key=True, index=True)
    nombre_negocio = Column(String(200), default="TechStock")
    nit = Column(String(50), default="")
    direccion = Column(Text, default="")
    telefono = Column(String(50), default="")
    email = Column(String(100), default="")
    logo_path = Column(String(255), default="")
    moneda_simbolo = Column(String(10), default="$")
    moneda_codigo = Column(String(10), default="COP")
    mensaje_recibo = Column(Text, default="Gracias por su compra")
    pie_factura = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    local = relationship("Local", back_populates="configuracion")

    def __repr__(self):
        return f"<Configuracion(id={self.id}, negocio='{self.nombre_negocio}')>"


# ─────────────────────────────────────────────
#  CLIENTES
# ─────────────────────────────────────────────

class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (
        Index("ix_clientes_local_activo", "local_id", "activo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    empresa = Column(String(200), default="")
    tipo_documento = Column(String(20), default="CC")
    documento = Column(String(50), default="", index=True)
    telefono = Column(String(50), default="")
    email = Column(String(100), default="")
    direccion = Column(Text, default="")
    notas = Column(Text, default="")
    saldo_credito = Column(Float, default=0.0)
    activo = Column(Boolean, default=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    ventas = relationship("Venta", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente(id={self.id}, nombre='{self.nombre}')>"


# ─────────────────────────────────────────────
#  VENTAS / PUNTO DE VENTA
# ─────────────────────────────────────────────

class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        Index("ix_ventas_fecha_estado", "fecha", "estado"),
        Index("ix_ventas_local_fecha_estado", "local_id", "fecha", "estado"),
        UniqueConstraint("numero_venta", "local_id", name="uq_ventas_numero_local"),
    )

    id = Column(Integer, primary_key=True, index=True)
    numero_venta = Column(String(50), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    cliente_nombre = Column(String(200), default="Consumidor Final")
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    subtotal = Column(Float, nullable=False)
    descuento_total = Column(Float, default=0.0)
    impuesto_total = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    metodo_pago = Column(String(50), nullable=False)
    monto_recibido = Column(Float, default=0.0)
    cambio = Column(Float, default=0.0)
    estado = Column(String(20), default="COMPLETADA", index=True)
    notas = Column(Text, default="")
    caja_id = Column(Integer, ForeignKey("cajas.id"), nullable=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    fecha = Column(DateTime, default=datetime.now, index=True)
    created_at = Column(DateTime, default=datetime.now)

    cliente = relationship("Cliente", back_populates="ventas")
    vendedor = relationship("Usuario", foreign_keys=[vendedor_id])
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    caja = relationship("Caja", back_populates="ventas")

    @property
    def costo_total(self):
        return round(sum(d.precio_costo * d.cantidad for d in self.detalles), 2)

    @property
    def ganancia_total(self):
        return round(sum(d.ganancia for d in self.detalles), 2)

    def __repr__(self):
        return f"<Venta(id={self.id}, numero='{self.numero_venta}', total={self.total})>"


class DetalleVenta(Base):
    __tablename__ = "detalle_venta"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    producto_nombre = Column(String(200), default="")
    producto_codigo = Column(String(50), default="")
    producto_referencia = Column(String(100), default="")
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    precio_costo = Column(Float, default=0.0)
    descuento_item = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto")

    @property
    def ganancia(self):
        return round(self.subtotal - (self.precio_costo * self.cantidad), 2)

    def __repr__(self):
        return f"<DetalleVenta(id={self.id}, venta_id={self.venta_id}, producto='{self.producto_nombre}')>"


# ─────────────────────────────────────────────
#  CAJA REGISTRADORA
# ─────────────────────────────────────────────

class Caja(Base):
    __tablename__ = "cajas"
    __table_args__ = (
        Index("ix_cajas_usuario_estado", "usuario_id", "estado"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    numero_caja = Column(Integer, default=1)
    monto_apertura = Column(Float, nullable=False)
    monto_cierre_esperado = Column(Float, nullable=True)
    monto_cierre_real = Column(Float, nullable=True)
    diferencia = Column(Float, nullable=True)
    estado = Column(String(20), default="ABIERTA", index=True)
    fecha_apertura = Column(DateTime, nullable=False, default=datetime.now)
    fecha_cierre = Column(DateTime, nullable=True)
    notas_cierre = Column(Text, default="")
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    movimientos = relationship("MovimientoCaja", back_populates="caja", cascade="all, delete-orphan")
    ventas = relationship("Venta", back_populates="caja")

    @property
    def total_ingresos(self):
        return sum(m.monto for m in self.movimientos if m.tipo == "INGRESO")

    @property
    def total_egresos(self):
        return sum(m.monto for m in self.movimientos if m.tipo == "EGRESO")

    @property
    def saldo_esperado(self):
        return self.monto_apertura + self.total_ingresos - self.total_egresos

    def __repr__(self):
        return f"<Caja(id={self.id}, usuario_id={self.usuario_id}, estado='{self.estado}')>"


class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, index=True)
    caja_id = Column(Integer, ForeignKey("cajas.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)
    concepto = Column(String(200), nullable=False)
    monto = Column(Float, nullable=False)
    referencia_tipo = Column(String(50), nullable=True)
    referencia_id = Column(Integer, nullable=True)
    local_id = Column(Integer, ForeignKey("locales.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    caja = relationship("Caja", back_populates="movimientos")

    def __repr__(self):
        return f"<MovimientoCaja(id={self.id}, caja_id={self.caja_id}, tipo='{self.tipo}')>"
