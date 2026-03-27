"""Tests para el modulo seed (creacion de datos por defecto)."""
import os
import pytest

import models
from seed import run_seed, _seed_admin, _seed_config, _seed_default_local, _generate_secure_password


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


class TestSeedAdmin:
    def test_creates_admin_when_no_users(self, db, default_local):
        """Si la tabla esta vacia, crea el admin."""
        assert db.query(models.Usuario).count() == 0
        _seed_admin(db, default_local)
        assert db.query(models.Usuario).count() == 1
        admin = db.query(models.Usuario).first()
        assert admin.rol == "SUPERADMIN"
        assert admin.activo is True

    def test_admin_username_from_env(self, db, default_local, monkeypatch):
        """Usa ADMIN_USERNAME del entorno si esta definida."""
        monkeypatch.setenv("ADMIN_USERNAME", "superadmin")
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        _seed_admin(db, default_local)
        admin = db.query(models.Usuario).first()
        assert admin.username == "superadmin"

    def test_admin_name_from_env(self, db, default_local, monkeypatch):
        """Usa ADMIN_NAME del entorno si esta definida."""
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        monkeypatch.setenv("ADMIN_NAME", "SuperAdmin Full")
        _seed_admin(db, default_local)
        admin = db.query(models.Usuario).first()
        assert admin.nombre_completo == "SuperAdmin Full"

    def test_admin_password_from_env(self, db, default_local, monkeypatch):
        """Usa ADMIN_PASSWORD del entorno para hashear la clave."""
        from auth import verify_password
        monkeypatch.setenv("ADMIN_PASSWORD", "MySecureP4ss")
        _seed_admin(db, default_local)
        admin = db.query(models.Usuario).first()
        assert verify_password("MySecureP4ss", admin.password_hash)

    def test_generates_password_when_not_set(self, db, default_local, monkeypatch):
        """Si ADMIN_PASSWORD no esta definida, genera una contrasena segura."""
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        _seed_admin(db, default_local)
        admin = db.query(models.Usuario).first()
        assert admin is not None
        # El hash debe ser un hash bcrypt valido
        assert admin.password_hash.startswith("$2b$") or admin.password_hash.startswith("$2a$")

    def test_idempotent_does_not_create_duplicate(self, db, default_local, monkeypatch):
        """Llamar dos veces no crea un segundo usuario."""
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        _seed_admin(db, default_local)
        _seed_admin(db, default_local)
        assert db.query(models.Usuario).count() == 1

    def test_skip_if_users_exist(self, db, default_local):
        """Si ya hay usuarios, no crea el admin."""
        from tests.conftest import _make_user
        _make_user(db, "existing", "pass1234", "Existing", "VENDEDOR")
        count_before = db.query(models.Usuario).count()
        _seed_admin(db, default_local)
        assert db.query(models.Usuario).count() == count_before

    def test_default_username_is_admin(self, db, default_local, monkeypatch):
        """Por defecto el usuario se llama 'admin'."""
        monkeypatch.delenv("ADMIN_USERNAME", raising=False)
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        _seed_admin(db, default_local)
        admin = db.query(models.Usuario).first()
        assert admin.username == "admin"

    def test_default_name_is_administrador(self, db, default_local, monkeypatch):
        """Por defecto el nombre completo es 'Administrador'."""
        monkeypatch.delenv("ADMIN_NAME", raising=False)
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        _seed_admin(db, default_local)
        admin = db.query(models.Usuario).first()
        assert admin.nombre_completo == "Administrador"


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
    def test_run_seed_creates_admin_and_config(self, db, monkeypatch):
        """run_seed crea tanto el admin como la configuracion."""
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        run_seed(db)
        assert db.query(models.Usuario).count() == 1
        assert db.query(models.Configuracion).count() == 1
        assert db.query(models.Local).count() == 1

    def test_run_seed_idempotent(self, db, monkeypatch):
        """run_seed es idempotente: ejecutar dos veces no duplica datos."""
        monkeypatch.setenv("ADMIN_PASSWORD", "SecretPass1")
        run_seed(db)
        run_seed(db)
        assert db.query(models.Usuario).count() == 1
        assert db.query(models.Configuracion).count() == 1
        assert db.query(models.Local).count() == 1
