"""
Inicialización de datos por defecto para TechStock.
Se ejecuta al iniciar la app. Todas las operaciones son idempotentes.
"""
import os
import logging
from sqlalchemy.orm import Session
from auth import hash_password
import models

logger = logging.getLogger("techstock.seed")


def run_seed(db: Session):
    """Crea datos por defecto si no existen."""
    _seed_admin(db)
    _seed_config(db)


def _seed_admin(db: Session):
    """Crea el usuario admin por defecto si la tabla está vacía.

    Lee credenciales desde variables de entorno (usadas por el instalador):
      ADMIN_USERNAME  (default: admin)
      ADMIN_PASSWORD  (default: admin123)
      ADMIN_NAME      (default: Administrador)
    """
    count = db.query(models.Usuario).count()
    if count > 0:
        return

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    fullname = os.environ.get("ADMIN_NAME", "Administrador")

    admin = models.Usuario(
        username=username,
        password_hash=hash_password(password),
        nombre_completo=fullname,
        rol="ADMIN",
        activo=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Usuario admin '%s' creado", username)


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
    logger.info("Configuracion del negocio creada")
