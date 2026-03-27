"""
Fixtures compartidos para la suite de tests de TechStock.
Usa SQLite in-memory con StaticPool para tests rapidos y aislados.
"""
import os
import sys

# Configurar entorno de test ANTES de cualquier import de la app
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TESTING"] = "1"

# Asegurar que el directorio raiz este en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from database import Base, engine, SessionLocal, get_db
from auth import hash_password, create_session_cookie, COOKIE_NAME
import models


# ── Setup/Teardown de BD por test ─────────────────────────────

@pytest.fixture(autouse=True)
def _setup_db():
    """Crea tablas antes de cada test, las elimina despues."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ── Session de BD ─────────────────────────────────────────────

@pytest.fixture
def db(_setup_db):
    """Sesion de base de datos para operaciones directas en tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── TestClient (sin autenticacion) ────────────────────────────

@pytest.fixture
def client(db):
    """TestClient sin autenticacion. Redirige a /login en rutas protegidas."""
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────

def _make_user(db, username, password, nombre, rol):
    """Crea un usuario en la BD de test."""
    user = models.Usuario(
        username=username,
        password_hash=hash_password(password),
        nombre_completo=nombre,
        rol=rol,
        activo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_client(client, user):
    """Agrega cookie de sesion al client para autenticacion."""
    cookie = create_session_cookie(user.id, user.username)
    client.cookies.set(COOKIE_NAME, cookie)
    return client


# ── Fixtures de Usuarios ──────────────────────────────────────

@pytest.fixture
def admin_user(db):
    """Usuario con rol ADMIN."""
    return _make_user(db, "admin", "admin12345", "Admin Test", "ADMIN")


@pytest.fixture
def vendedor_user(db):
    """Usuario con rol VENDEDOR."""
    return _make_user(db, "vendedor", "vendedor123", "Vendedor Test", "VENDEDOR")


@pytest.fixture
def bodeguero_user(db):
    """Usuario con rol BODEGUERO."""
    return _make_user(db, "bodeguero", "bodeguero123", "Bodeguero Test", "BODEGUERO")


# ── Clients Autenticados ──────────────────────────────────────

@pytest.fixture
def admin_client(client, admin_user):
    """TestClient autenticado como ADMIN."""
    return _auth_client(client, admin_user)


@pytest.fixture
def vendedor_client(client, vendedor_user):
    """TestClient autenticado como VENDEDOR."""
    return _auth_client(client, vendedor_user)


@pytest.fixture
def bodeguero_client(client, bodeguero_user):
    """TestClient autenticado como BODEGUERO."""
    return _auth_client(client, bodeguero_user)


# ── Fixtures de Datos ─────────────────────────────────────────

@pytest.fixture
def sample_config(db):
    """Configuracion del negocio de prueba."""
    config = models.Configuracion(
        nombre_negocio="Test Store",
        moneda_simbolo="$",
        moneda_codigo="COP",
        mensaje_recibo="Gracias por su compra",
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@pytest.fixture
def sample_categoria(db):
    """Categoria de prueba."""
    cat = models.Categoria(nombre="Electronicos", descripcion="Productos electronicos")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture
def sample_proveedor(db):
    """Proveedor de prueba."""
    prov = models.Proveedor(
        nombre="Proveedor Test",
        contacto="Juan Perez",
        telefono="3001234567",
        email="prov@test.com",
        nit_ruc="900123456",
        activo=True,
    )
    db.add(prov)
    db.commit()
    db.refresh(prov)
    return prov


@pytest.fixture
def sample_producto(db, sample_categoria, sample_proveedor):
    """Producto de prueba con stock."""
    prod = models.Producto(
        codigo="PROD-001",
        nombre="Laptop Test",
        descripcion="Laptop de prueba",
        categoria_id=sample_categoria.id,
        proveedor_id=sample_proveedor.id,
        precio_costo=1000.0,
        precio_venta=1500.0,
        stock_actual=50.0,
        stock_minimo=5.0,
        unidad_medida="UND",
        activo=True,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


@pytest.fixture
def sample_cliente(db):
    """Cliente de prueba."""
    cli = models.Cliente(
        nombre="Cliente Test",
        tipo_documento="CC",
        documento="1234567890",
        telefono="3109876543",
        email="cli@test.com",
        activo=True,
    )
    db.add(cli)
    db.commit()
    db.refresh(cli)
    return cli


@pytest.fixture
def sample_deuda(db, sample_proveedor):
    """Deuda de prueba."""
    from datetime import datetime, timedelta
    deuda = models.Deuda(
        concepto="Compra de mercancia",
        acreedor_nombre=sample_proveedor.nombre,
        acreedor_tipo="PROVEEDOR",
        proveedor_id=sample_proveedor.id,
        monto_total=500000.0,
        monto_pagado=0.0,
        fecha_deuda=datetime.now(),
        fecha_vencimiento=datetime.now() + timedelta(days=30),
        estado="PENDIENTE",
    )
    db.add(deuda)
    db.commit()
    db.refresh(deuda)
    return deuda


@pytest.fixture
def sample_factura(db):
    """Factura de prueba."""
    from datetime import datetime, timedelta
    factura = models.Factura(
        numero_factura="FAC-0001",
        cliente_nombre="Cliente Factura Test",
        cliente_documento="9876543210",
        concepto="Venta de equipos",
        monto_total=1000000.0,
        monto_cobrado=0.0,
        fecha_emision=datetime.now(),
        fecha_vencimiento=datetime.now() + timedelta(days=30),
        estado="PENDIENTE",
    )
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


@pytest.fixture
def sample_gasto(db):
    """Gasto de prueba."""
    from datetime import datetime
    gasto = models.Gasto(
        concepto="Arriendo local",
        tipo="DIRECTO",
        categoria_gasto="Arriendo",
        monto=2000000.0,
        fecha=datetime.now(),
        metodo_pago="TRANSFERENCIA",
        comprobante="TRX-001",
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@pytest.fixture
def caja_abierta(db, admin_user):
    """Caja abierta para el admin."""
    from datetime import datetime
    caja = models.Caja(
        usuario_id=admin_user.id,
        monto_apertura=100000.0,
        estado="ABIERTA",
        fecha_apertura=datetime.now(),
    )
    db.add(caja)
    db.commit()
    db.refresh(caja)
    return caja
