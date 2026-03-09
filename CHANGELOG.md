# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado basado en [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.0.0] — 2026-03-09

### Añadido
- **Dashboard** con métricas en tiempo real: valor del inventario, stock bajo, movimientos del día y últimos movimientos
- **Módulo Productos**: CRUD completo con código, nombre, descripción, categoría, proveedor, precio costo/venta, stock actual/mínimo, unidad de medida y cálculo automático de margen
- **Módulo Categorías**: CRUD con modal inline y 14 categorías sugeridas para tiendas tech
- **Módulo Proveedores**: CRUD con página de detalle que muestra productos asociados e historial de entradas
- **Módulo Inventario**: registro de movimientos tipo ENTRADA, SALIDA y AJUSTE con historial paginado y filtros por producto, tipo y rango de fechas
- **Módulo Reportes**:
  - Reporte de stock actual con filtros por categoría y alerta de stock bajo
  - Reporte de movimientos por período con totales de entradas/salidas
  - Exportación a PDF (landscape A4) con ReportLab para ambos reportes
- **Arquitectura multi-equipo**: servidor único accesible desde cualquier PC en la red local via browser
- SQLite en modo WAL para soporte de múltiples lectores concurrentes
- Scripts `install.bat` y `start.bat` para facilitar el uso en Windows
- Filtros Jinja2 personalizados: `moneda` y `numero` en instancia compartida (`templates_config.py`)
- UI responsive con Bootstrap 5, sidebar colapsable y Bootstrap Icons
