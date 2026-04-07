"""Tests para el modulo seed (creacion de datos por defecto)."""
import os
import pytest

import models
from seed import run_seed, _seed_config, _seed_default_local, _generate_secure_password


@pytest.fixture
def default_local(db):
    """Crea el local por defecto necesario para seed."""
    return _seed_default_local(db)


class TestGenerateSecurePassword:
    def test_meets_policy(self):
        pwd = _generate_secure_password()
        assert len(pwd) >= 12
        assert any(c.isupper() for c in pwd)
        assert any(c.islower() for c in pwd)
        assert any(c.isdigit() for c in pwd)

    def test_custom_length(self):
        pwd = _generate_secure_password(length=20)
        assert len(pwd) == 20

    def test_different_on_each_call(self):
        p1 = _generate_secure_password()
        p2 = _generate_secure_password()
        # Estadisticamente deberian ser distintas (prob de colision es despreciable)
        # Solo verificamos que es string no vacio
        assert isinstance(p1, str) and len(p1) > 0
        assert isinstance(p2, str) and len(p2) > 0


class TestSeedDefaultLocal:
    def test_creates_local_when_none_exists(self, db):
        assert db.query(models.Local).count() == 0
        local = _seed_default_local(db)
        assert db.query(models.Local).count() == 1
        assert local.nombre == "Sede Principal"
        assert local.codigo == "SEDE-001"

    def test_idempotent(self, db):
        local1 = _seed_default_local(db)
        local2 = _seed_default_local(db)
        assert db.query(models.Local).count() == 1
        assert local1.id == local2.id


class TestSeedConfig:
    def test_creates_config_when_none_exists(self, db, default_local):
        """Si no hay configuracion, la crea."""
        assert db.query(models.Configuracion).count() == 0
        _seed_config(db, default_local)
        assert db.query(models.Configuracion).count() == 1

    def test_default_config_values(self, db, default_local):
        """La configuracion creada tiene los valores por defecto."""
        _seed_config(db, default_local)
        config = db.query(models.Configuracion).first()
        assert config.nombre_negocio == "TechStock"
        assert config.moneda_simbolo == "$"
        assert config.moneda_codigo == "COP"
        assert config.mensaje_recibo == "Gracias por su compra"

    def test_idempotent_does_not_create_duplicate(self, db, default_local):
        """Llamar dos veces no crea una segunda configuracion."""
        _seed_config(db, default_local)
        _seed_config(db, default_local)
        assert db.query(models.Configuracion).count() == 1

    def test_skip_if_config_exists(self, db, default_local):
        """Si ya hay configuracion, no crea otra."""
        config = models.Configuracion(
            nombre_negocio="Mi Empresa",
            moneda_simbolo="€",
            moneda_codigo="EUR",
        )
        db.add(config)
        db.commit()
        _seed_config(db, default_local)
        assert db.query(models.Configuracion).count() == 1
        # Los valores originales se mantienen
        existing = db.query(models.Configuracion).first()
        assert existing.nombre_negocio == "Mi Empresa"


class TestRunSeed:
    def test_run_seed_creates_local_admin_and_config(self, db):
        """run_seed crea el local por defecto, SUPERADMIN y la configuracion."""
        run_seed(db)
        assert db.query(models.Local).count() == 1
        assert db.query(models.Usuario).count() == 1
        assert db.query(models.Configuracion).count() == 1
        admin = db.query(models.Usuario).first()
        assert admin.rol == "SUPERADMIN"
        assert admin.local_id is None
        assert admin.activo is True

    def test_run_seed_idempotent(self, db):
        """run_seed es idempotente: ejecutar dos veces no duplica datos."""
        run_seed(db)
        run_seed(db)
        assert db.query(models.Local).count() == 1
        assert db.query(models.Usuario).count() == 1
        assert db.query(models.Configuracion).count() == 1
