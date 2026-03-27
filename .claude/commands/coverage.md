# Skill: Analisis y Mejora de Cobertura de Tests

Identifica codigo sin tests y genera tests para alcanzar la cobertura objetivo.

## Instrucciones

### 1. Medir cobertura actual
```bash
pytest --cov --cov-report=term-missing --tb=short -q
```
Captura el porcentaje global y las lineas sin cubrir por archivo.

### 2. Analizar brechas
- Identificar archivos con menor cobertura (priorizar routers/ y utils/)
- Para cada archivo con brechas, identificar:
  - Ramas de codigo no cubiertas (if/else, try/except)
  - Endpoints sin tests
  - Funciones utilitarias sin tests
  - Edge cases no probados (inputs vacios, duplicados, limites)

### 3. Priorizar por riesgo
Ordenar brechas por impacto:
1. **Critico**: Endpoints financieros sin tests (ventas, deudas, facturas, caja)
2. **Alto**: Endpoints CRUD sin tests (crear, editar, eliminar)
3. **Medio**: Validaciones y edge cases
4. **Bajo**: Rutas de solo lectura (listados, detalles)

### 4. Generar tests
Para cada brecha priorizada:
- Crear test en `tests/test_<modulo>.py` existente
- Usar fixtures de `conftest.py` (client, admin_user, sample_local, db_session, etc.)
- Seguir patron del proyecto:
  ```python
  def test_nombre_descriptivo(client, admin_user, sample_local, db_session):
      # Arrange: crear datos necesarios con local_id=sample_local.id
      # Act: hacer request HTTP
      # Assert: verificar status code y estado de DB
  ```
- Incluir `local_id=sample_local.id` en toda entidad creada
- Verificar tanto el happy path como los errores esperados

### 5. Verificar mejora
```bash
pytest --cov --cov-report=term-missing --tb=short -q
```
Comparar antes/despues. Objetivo: 95%+ cobertura global.

### 6. Reporte final
- Cobertura antes vs despues
- Tests agregados (cantidad y modulos)
- Brechas restantes y justificacion (si alguna no vale la pena cubrir)

## Scope
$ARGUMENTS
