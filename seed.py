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
    default_local = _seed_default_local(db)
    _seed_superadmin(db)
    _seed_config(db, default_local)


def _seed_default_local(db: Session) -> models.Local:
    """Crea el local por defecto 'Sede Principal' si no existen locales."""
    local = db.query(models.Local).first()
    if local:
        return local

    local = models.Local(
        nombre="Sede Principal",
        codigo="SEDE-001",
        activo=True,
    )
    db.add(local)
    db.commit()
    logger.info("Local por defecto 'Sede Principal' creado (id=%s)", local.id)
    return local


def _seed_superadmin(db: Session):
    """Crea el usuario SUPERADMIN si no existen usuarios."""
    count = db.query(models.Usuario).count()
    if count > 0:
        return

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    nombre = os.environ.get("ADMIN_NAME", "Administrador")

    if not password:
        password = _generate_secure_password()
        logger.warning("=" * 50)
        logger.warning("SUPERADMIN creado con credenciales:")
        logger.warning("  Usuario:    %s", username)
        logger.warning("  Contraseña: %s", password)
        logger.warning("  (Cambie la contraseña después del primer login)")
        logger.warning("=" * 50)

    admin = models.Usuario(
        username=username,
        password_hash=hash_password(password),
        nombre_completo=nombre,
        rol="SUPERADMIN",
        local_id=None,
        activo=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Usuario SUPERADMIN '%s' creado (id=%s)", username, admin.id)


def _seed_config(db: Session, default_local: models.Local):
    """Crea la configuración por defecto para el local principal si no existe."""
    count = db.query(models.Configuracion).count()
    if count > 0:
        return

    config = models.Configuracion(
        nombre_negocio="TechStock",
        moneda_simbolo="$",
        moneda_codigo="COP",
        mensaje_recibo="Gracias por su compra",
        local_id=default_local.id,
    )
    db.add(config)
    db.commit()
    logger.info("Configuracion del negocio creada para local '%s'", default_local.nombre)
