"""Queries comunes reutilizables para evitar duplicación en routers."""
from sqlalchemy.orm import Session
import models


def categorias_activas(db: Session, local_id: int = None):
    """Categorías activas ordenadas por nombre."""
    query = db.query(models.Categoria).filter(models.Categoria.activo == True)
    if local_id is not None:
        query = query.filter(models.Categoria.local_id == local_id)
    return query.order_by(models.Categoria.nombre).all()


def proveedores_activos(db: Session, local_id: int = None):
    """Proveedores activos ordenados por nombre."""
    query = db.query(models.Proveedor).filter(models.Proveedor.activo == True)
    if local_id is not None:
        query = query.filter(models.Proveedor.local_id == local_id)
    return query.order_by(models.Proveedor.nombre).all()


def acreedores_activos(db: Session, local_id: int = None):
    """Acreedores activos ordenados por nombre."""
    query = db.query(models.Acreedor).filter(models.Acreedor.activo == True)
    if local_id is not None:
        query = query.filter(models.Acreedor.local_id == local_id)
    return query.order_by(models.Acreedor.nombre).all()


def productos_activos(db: Session, local_id: int = None):
    """Productos activos ordenados por nombre."""
    query = db.query(models.Producto).filter(models.Producto.activo == True)
    if local_id is not None:
        query = query.filter(models.Producto.local_id == local_id)
    return query.order_by(models.Producto.nombre).all()


def productos_con_stock(db: Session, local_id: int = None):
    """Productos activos con stock > 0, ordenados por nombre."""
    query = db.query(models.Producto).filter(
        models.Producto.activo == True,
        models.Producto.stock_actual > 0
    )
    if local_id is not None:
        query = query.filter(models.Producto.local_id == local_id)
    return query.order_by(models.Producto.nombre).all()


def clientes_activos(db: Session, local_id: int = None):
    """Clientes activos ordenados por nombre."""
    query = db.query(models.Cliente).filter(models.Cliente.activo == True)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    return query.order_by(models.Cliente.nombre).all()


def vendedores_activos(db: Session, local_id: int = None):
    """Usuarios activos ordenados por nombre."""
    query = db.query(models.Usuario).filter(models.Usuario.activo == True)
    if local_id is not None:
        query = query.filter(models.Usuario.local_id == local_id)
    return query.order_by(models.Usuario.nombre_completo).all()
