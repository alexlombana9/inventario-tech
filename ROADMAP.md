# Roadmap — TechStock

Este archivo describe las funcionalidades planificadas para versiones futuras, ordenadas por prioridad.

---

## v1.1 — Ventas y Punto de Venta (POS)

> Objetivo: permitir registrar ventas directamente desde el sistema y descontar automáticamente el stock.

- [ ] Módulo **Clientes**: CRUD con nombre, documento, teléfono, email, dirección e historial de compras
- [ ] **Carrito de venta**: seleccionar múltiples productos con cantidad y precio
- [ ] **Métodos de pago**: efectivo, tarjeta, transferencia, crédito
- [ ] Descuento automático de stock al registrar una venta
- [ ] Vista de historial de ventas con filtros por fecha, cliente y estado
- [ ] Búsqueda de productos por código de barras en el POS

---

## v1.2 — Caja y Cuadre

> Objetivo: control diario del dinero en caja.

- [ ] **Apertura de caja**: registrar monto inicial al empezar el día
- [ ] **Movimientos de caja**: ingresos y egresos manuales con descripción
- [ ] **Cierre de caja**: resumen del día (ventas, ingresos, egresos, saldo final)
- [ ] Historial de cierres de caja por fecha
- [ ] Diferencia entre monto esperado y monto contado físicamente

---

## v1.3 — Facturación y Comprobantes

> Objetivo: generar comprobantes internos imprimibles para ventas.

- [ ] **Comprobante de venta** en PDF: encabezado del negocio, ítems, subtotal, impuestos, total
- [ ] **Configuración del negocio**: nombre, NIT/RUC, dirección, teléfono, logo para incluir en comprobantes
- [ ] Numeración automática y consecutiva de comprobantes
- [ ] Reimpresión de comprobantes anteriores
- [ ] Comprobante de entrada de mercancía (orden de recepción)

---

## v1.4 — Reportes Avanzados

> Objetivo: análisis más profundo del negocio.

- [ ] **Reporte de ventas**: por período, por producto, por cliente, por vendedor
- [ ] **Productos más vendidos**: ranking por cantidad y por valor
- [ ] **Margen de ganancia real**: costo vs. precio de venta por período
- [ ] **Rotación de inventario**: productos con poco movimiento
- [ ] **Gráficas**: ventas por día/semana/mes (Chart.js)
- [ ] Exportación a Excel (`.xlsx`) además de PDF

---

## v1.5 — Órdenes de Compra

> Objetivo: gestionar el proceso de compra a proveedores.

- [ ] Crear órdenes de compra a proveedores con lista de productos y cantidades
- [ ] Estado de orden: Borrador → Enviada → Recibida
- [ ] Al marcar como Recibida, generar automáticamente las entradas de inventario
- [ ] Historial de órdenes por proveedor

---

## v2.0 — Multi-usuario y Seguridad

> Objetivo: control de acceso por usuario con permisos.

- [ ] **Autenticación**: login con usuario y contraseña (JWT o sesiones)
- [ ] **Roles**: Administrador, Vendedor, Bodeguero (permisos diferenciados)
- [ ] **Auditoría**: registrar qué usuario realizó cada movimiento/venta
- [ ] Cambio de contraseña y gestión de usuarios desde el panel admin
- [ ] Bloqueo de acceso a módulos según el rol

---

## v2.1 — Mejoras de Infraestructura

- [ ] Migración opcional a **PostgreSQL** para mayor rendimiento con muchos usuarios
- [ ] **Backup automático** de la base de datos (programable por hora/día)
- [ ] Restauración de backup desde la interfaz
- [ ] Script de instalación con `pip install` o ejecutable `.exe` empaquetado
- [ ] Soporte para múltiples sucursales / locales

---

## Ideas / Backlog (sin versión asignada)

- Integración con lector de código de barras (USB/Bluetooth)
- App móvil para consulta de stock (PWA)
- Notificaciones por email cuando el stock baja del mínimo
- Importación masiva de productos desde Excel/CSV
- Módulo de garantías y servicio técnico
- Soporte para series/IMEI en productos de tecnología

---

> **¿Tienes una sugerencia?** Abre un [Issue](../../issues/new) describiendo la funcionalidad que necesitas.
