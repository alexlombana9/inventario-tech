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
