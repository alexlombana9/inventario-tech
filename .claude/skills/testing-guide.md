# Guia de Testing — TechStock

## Comandos
```bash
pytest --tb=short -q              # Suite completa (651+ tests)
pytest tests/test_ventas.py -v    # Modulo especifico
pytest -k "test_crear_venta"      # Test especifico por nombre
pytest --cov --cov-report=html    # Cobertura HTML en htmlcov/
pytest --cov --cov-report=term    # Cobertura en terminal
```

## Entorno de Tests
- DB: SQLite in-memory con `StaticPool` (env: `DATABASE_URL=sqlite://`, `TESTING=1`)
- CSRF deshabilitado automaticamente cuando `TESTING=1`
- Config en `pytest.ini` con cobertura automatica y strict markers

## Estructura de un Test
```python
def test_crear_entidad(client, admin_user, sample_local, db_session):
    # Arrange — crear datos con local_id
    entidad = models.MiEntidad(nombre="Test", local_id=sample_local.id)
    db_session.add(entidad); db_session.commit()
    # Act — HTTP request
    response = client.post("/mi-modulo/nuevo", data={"nombre": "Nuevo", "csrf_token": "x"})
    # Assert — status code + estado en DB
    assert response.status_code == 303
    assert db_session.query(models.MiEntidad).filter_by(nombre="Nuevo").first()
```

## Fixtures Principales (conftest.py)
| Fixture | Proporciona |
|---------|-------------|
| `db_session` | Session SQLAlchemy (SQLite in-memory, rollback auto) |
| `client` | TestClient httpx autenticado como admin |
| `admin_user` | Usuario rol=ADMIN con local_id=sample_local.id |
| `superadmin_user` | Usuario rol=SUPERADMIN con local_id=None |
| `sample_local` | Local "Sede Principal" (id asignado) |
| `sample_producto` | Producto con categoria, proveedor, stock, local_id |
| `sample_categoria` | Categoria activa con local_id |
| `sample_proveedor` | Proveedor activo con local_id |
| `sample_cliente` | Cliente activo con local_id |
| `sample_caja_abierta` | Caja estado=ABIERTA con local_id |

## Flujo TDD para Bug Fixes
1. Escribir test que reproduzca el bug (debe fallar)
2. Ejecutar `pytest tests/test_modulo.py::test_bug -v` — confirmar fallo
3. Aplicar fix minimo en el codigo
4. Ejecutar mismo test — confirmar que pasa
5. Ejecutar suite completa — confirmar que no hay regresiones

## Analisis de Cobertura
1. `pytest --cov --cov-report=term-missing` — identificar lineas sin cubrir
2. Priorizar por riesgo: rutas POST (mutaciones) > GET (lectura)
3. Priorizar modulos financieros: ventas, deudas, facturas, caja
4. Generar tests para ramas no cubiertas (error handling, edge cases)
5. Verificar: `pytest --tb=short -q` — todo verde
