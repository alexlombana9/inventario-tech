"""
Inicialización de datos por defecto para TechStock.
Se ejecuta al iniciar la app. Todas las operaciones son idempotentes.
"""
from sqlalchemy.orm import Session
from auth import hash_password
import models


def run_seed(db: Session):
    """Crea datos por defecto si no existen."""
    _seed_admin(db)
    _seed_config(db)


def _seed_admin(db: Session):
    """Crea el usuario admin por defecto si la tabla está vacía."""
    count = db.query(models.Usuario).count()
    if count > 0:
        return

    admin = models.Usuario(
        username="admin",
        password_hash=hash_password("admin123"),
        nombre_completo="Administrador",
        rol="ADMIN",
        activo=True,
    )
    db.add(admin)
    db.commit()
    print("  [Seed] Usuario admin creado (usuario: admin, contraseña: admin123)")


def _seed_config(db: Session):
    """Crea la configuración por defecto si no existe."""
    count = db.query(models.Configuracion).count()
    if count > 0:
        return

    config = models.Configuracion(
        nombre_negocio="TechStock",
        moneda_simbolo="$",
        moneda_codigo="COP",
        mensaje_recibo="Gracias por su compra",
    )
    db.add(config)
    db.commit()
    print("  [Seed] Configuración del negocio creada")
