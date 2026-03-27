"""
Inicialización de datos por defecto para TechStock.
Se ejecuta al iniciar la app. Todas las operaciones son idempotentes.
"""
import os
import secrets
import string
import logging
from sqlalchemy.orm import Session
from auth import hash_password
import models

logger = logging.getLogger("techstock.seed")


def _generate_secure_password(length: int = 12) -> str:
    """Genera una contraseña segura aleatoria que cumple la política."""
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in pwd) and
            any(c.islower() for c in pwd) and
            any(c.isdigit() for c in pwd)):
            return pwd


def run_seed(db: Session):
    """Crea datos por defecto si no existen."""
    _seed_admin(db)
    _seed_config(db)


def _seed_admin(db: Session):
    """Crea el usuario admin por defecto si la tabla está vacía.

    Lee credenciales desde variables de entorno (usadas por el instalador):
      ADMIN_USERNAME  (default: admin)
      ADMIN_PASSWORD  (si no se define, genera una segura y la muestra en consola)
      ADMIN_NAME      (default: Administrador)
    """
    count = db.query(models.Usuario).count()
    if count > 0:
        return

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    fullname = os.environ.get("ADMIN_NAME", "Administrador")

    generated = False
    if not password:
        password = _generate_secure_password()
        generated = True

    admin = models.Usuario(
        username=username,
        password_hash=hash_password(password),
        nombre_completo=fullname,
        rol="ADMIN",
        activo=True,
    )
    db.add(admin)
    db.commit()

    if generated:
        logger.warning("=" * 55)
        logger.warning("  CREDENCIALES ADMIN GENERADAS (cambiar al primer login)")
        logger.warning("  Usuario:    %s", username)
        logger.warning("  Contraseña: %s", password)
        logger.warning("=" * 55)
    else:
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
