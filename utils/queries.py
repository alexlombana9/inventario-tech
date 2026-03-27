"""Queries comunes reutilizables para evitar duplicación en routers."""
from sqlalchemy.orm import Session
import models


def categorias_activas(db: Session):
    """Categorías activas ordenadas por nombre."""
    return db.query(models.Categoria).filter(
        models.Categoria.activo == True
    ).order_by(models.Categoria.nombre).all()


def proveedores_activos(db: Session):
    """Proveedores activos ordenados por nombre."""
    return db.query(models.Proveedor).filter(
        models.Proveedor.activo == True
    ).order_by(models.Proveedor.nombre).all()


def acreedores_activos(db: Session):
    """Acreedores activos ordenados por nombre."""
    return db.query(models.Acreedor).filter(
        models.Acreedor.activo == True
    ).order_by(models.Acreedor.nombre).all()


def productos_activos(db: Session):
    """Productos activos ordenados por nombre."""
    return db.query(models.Producto).filter(
        models.Producto.activo == True
    ).order_by(models.Producto.nombre).all()


def productos_con_stock(db: Session):
    """Productos activos con stock > 0, ordenados por nombre."""
    return db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual > 0
    ).order_by(models.Producto.nombre).all()


def clientes_activos(db: Session):
    """Clientes activos ordenados por nombre."""
    return db.query(models.Cliente).filter(
        models.Cliente.activo == True
    ).order_by(models.Cliente.nombre).all()


def vendedores_activos(db: Session):
    """Usuarios activos ordenados por nombre."""
    return db.query(models.Usuario).filter(
        models.Usuario.activo == True
    ).order_by(models.Usuario.nombre_completo).all()
