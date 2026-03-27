# TechStock v3.0 — Guia Completa de Desarrollo

## Inicio Rapido (Orientacion Autonoma)

Al iniciar una nueva sesion, NO investigues el proyecto desde cero. Este documento tiene todo lo necesario.

- **Stack**: FastAPI 0.115 + SQLAlchemy 2.0 + PostgreSQL 16 + Jinja2 + Bootstrap 5.3 (SSR)
- **Tests**: `pytest --tb=short -q` (651 tests, 95% cobertura)
- **Dev server**: `python main.py` (0.0.0.0:8000, requiere PostgreSQL activo)
- **Skills disponibles**: 14 skills profesionales — ver seccion 15 para lista completa
- **Idioma del codigo**: Nombres de rutas, variables y UI en espanol. Comentarios y docstrings en espanol.
- **Multi-tenant**: Arquitectura por `local_id` — cada local opera de forma independiente

---

## 1. Stack Tecnologico

| Capa | Tecnologia | Version | Proposito |
|------|------------|---------|-----------|
| Backend | FastAPI | 0.115 | Framework web async, API REST |
| ORM | SQLAlchemy | 2.0.35 | Modelos, queries, migraciones |
| DB (prod) | PostgreSQL | 16 | Motor principal, portable o externo |
| DB (test) | SQLite | in-memory | Tests rapidos con StaticPool |
| Templates | Jinja2 | 3.1.4 | Server-side rendering |
| CSS | Bootstrap | 5.3 | UI responsive (local, sin CDN) |
| Icons | Bootstrap Icons | 1.11 | Iconografia (local, con fonts woff2) |
| Charts | Chart.js | 4.x | Graficas dashboard (local) |
| JS | Vanilla JS | ES6+ | Sin frameworks frontend |
| Auth | itsdangerous | 2.2.0 | Cookies firmadas (sesion + CSRF) |
| Passwords | bcrypt | 4.0+ | Hashing seguro |
| Excel | openpyxl | 3.1.5 | Exportacion/importacion Excel |
| PDF | ReportLab | 4.2+ | Generacion de recibos PDF |
| Server | Uvicorn | 0.30.6 | ASGI server |
| Forms | python-multipart | 0.0.12 | Parsing de formularios POST |
| Files | aiofiles | 23.2.1 | Manejo async de archivos |
| DB Driver | psycopg2-binary | 2.9+ | Conector PostgreSQL |
| Testing | pytest + httpx | 8.0+ | Suite de tests |
| Build | PyInstaller | 6.x | Empaquetado a .exe |
| Installer | Inno Setup | 6 | Instalador Windows |
| CI/CD | GitHub Actions | — | Tests en Python 3.10, 3.11, 3.12 |

### Principios Arquitectonicos

- **Server-Side Rendering (SSR)**: Jinja2 renderiza HTML completo, NO es SPA
- **100% Offline**: Todos los assets (Bootstrap, Icons, Chart.js) son locales en `static/vendor/`
- **PostgreSQL siempre**: SQLite solo para tests in-memory, nunca en produccion
- **PRG Pattern**: Todos los POST retornan `RedirectResponse(url, 303)`
- **Soft Delete**: Nunca `db.delete()`, siempre `activo=False` o `estado="ANULADO"`
- **Audit Trail**: Toda mutacion (CREATE/UPDATE/DELETE) registra `log_audit()`
- **Multi-tenant**: Todas las entidades tienen `local_id` FK a tabla `locales`

---

## 2. Arquitectura Multi-Tenant

### Concepto

Un unico deployment sirve multiples locales (sucursales). Cada local tiene inventario, ventas, configuracion y datos independientes. Un SUPERADMIN gestiona todos los locales desde un dashboard consolidado.

### Modelo de Tenant

```
Local (locales)
├── id, nombre, codigo (unique), direccion, telefono, email, ciudad, responsable
├── activo, created_at, updated_at
└── Todas las demas tablas tienen FK: local_id → locales.id
```

### Filtrado por local_id

Toda query en routers usa `get_local_id(request)` para obtener el local efectivo:

```python
from auth import get_local_id

local_id = get_local_id(request)
query = db.query(models.Producto).filter(models.Producto.activo == True)
if local_id is not None:
    query = query.filter(models.Producto.local_id == local_id)
```

**Reglas de `get_local_id()`:**
- Usuario normal → retorna `user.local_id` (siempre tiene uno)
- SUPERADMIN con local seleccionado → retorna `selected_local_id` (de cookie)
- SUPERADMIN sin local seleccionado → retorna `None` (ve todo)

### Cookie de seleccion de local

El SUPERADMIN selecciona un local via `/locales/{id}/seleccionar`, que escribe la cookie `techstock_selected_local`. El middleware la lee y la inyecta en `request.state.selected_local_id`.

### Unique Constraints compuestas

Las restricciones de unicidad son por local:
- `uq_categorias_nombre_local` (nombre + local_id)
- `uq_productos_codigo_local` (codigo + local_id)
- `uq_facturas_numero_local` (numero_factura + local_id)
- `uq_ventas_numero_local` (numero_venta + local_id)

### Numeros correlativos por local

`siguiente_numero(db, model, campo, prefijo, local_id)` genera secuencias independientes por local (FAC-0001, VTA-0001).

### Configuracion por local

`Configuracion` tiene `local_id` con unique constraint. Cada local tiene su propia configuracion (nombre negocio, moneda, recibo).

---

## 3. Estructura del Proyecto

```
inventario-tech/
├── main.py                  # App FastAPI, dashboard (30+ queries), startup, registro de routers
├── database.py              # Engine, SessionLocal, Base, get_db (PG/SQLite auto)
├── models.py                # 19 modelos SQLAlchemy (+Local, todas con local_id)
├── auth.py                  # Hash, cookies, sesion, CSRF, audit, permisos, RBAC, get_local_id
├── middleware.py             # AuthMiddleware: cookie → request.state.user + CSRF + local_id
├── templates_config.py      # Jinja2 config + filtros (moneda, numero) + csrf_token + is_superadmin
├── seed.py                  # Local default + SUPERADMIN + config (idempotente)
├── migrations.py            # 13+ migraciones idempotentes (sin Alembic, PostgreSQL only)
├── launcher.py              # GUI tkinter dark-theme: PG portable + server lifecycle
│
├── utils/
│   ├── __init__.py
│   ├── constants.py         # METODOS_PAGO, TIPOS_ACREEDOR, CATEGORIAS_GASTO
│   ├── financial.py         # actualizar_estado_pago(), siguiente_numero(local_id)
│   ├── pagination.py        # paginate(query, page, per_page) → (items, total, pages)
│   ├── excel.py             # generate_excel(title, headers, rows, ...) → BytesIO
│   ├── dashboard.py         # Funciones dashboard con filtro local_id
│   ├── queries.py           # categorias_activas, proveedores_activos, etc. (todas con local_id)
│   └── pdf.py               # Generacion de reportes PDF
│
├── routers/                 # 21 routers, 134+ endpoints
│   ├── __init__.py
│   ├── auth_router.py       # Login, logout, switch account (5 endpoints)
│   ├── usuarios.py          # CRUD usuarios + permisos + asignacion de local (6 endpoints)
│   ├── productos.py         # CRUD productos + Excel export (6 endpoints)
│   ├── categorias.py        # CRUD categorias con cascade protection (4 endpoints)
│   ├── proveedores.py       # CRUD proveedores + detalle con deudas (7 endpoints)
│   ├── clientes.py          # CRUD clientes + detalle con ventas (7 endpoints)
│   ├── inventario.py        # Entradas, salidas, ajustes, movimientos (6 endpoints)
│   ├── ventas.py            # POS, historial, detalle, recibo, anular (8 endpoints)
│   ├── caja.py              # Abrir, cerrar, estado, movimientos, historial (8 endpoints)
│   ├── deudas.py            # CRUD deudas + pagos + reporte (11 endpoints)
│   ├── facturas.py          # CRUD facturas + cobros + reporte + import Excel (11 endpoints)
│   ├── acreedores.py        # CRUD acreedores (6 endpoints)
│   ├── gastos.py            # CRUD gastos + filtros (7 endpoints)
│   ├── reportes.py          # Stock bajo, movimientos, Excel exports (7 endpoints)
│   ├── configuracion.py     # Config negocio por local (nombre, moneda, recibo) (3 endpoints)
│   ├── importar.py          # Import Excel categorias/productos/facturas (3 endpoints)
│   ├── backup.py            # Backup/restore DB completo (7 endpoints)
│   ├── perfil.py            # Perfil usuario + avatar (5 endpoints)
│   ├── auditoria.py         # Log de auditoria con filtros (1 endpoint)
│   ├── locales.py           # CRUD locales + seleccionar/deseleccionar (SUPERADMIN)
│   └── super_dashboard.py   # Dashboard consolidado multi-local (SUPERADMIN)
│
├── templates/               # 50 HTML templates
│   ├── base.html            # Layout maestro: sidebar, navbar, Bootstrap, selector de local
│   ├── index.html           # Dashboard con 7 graficas Chart.js
│   ├── auth/login.html      # Login con multi-cuenta
│   ├── productos/           # lista.html, form.html
│   ├── categorias/          # lista.html
│   ├── proveedores/         # lista.html, form.html, detalle.html
│   ├── clientes/            # lista.html, form.html, detalle.html
│   ├── inventario/          # entrada.html, ajuste.html, movimientos.html
│   ├── ventas/              # pos.html, historial.html, detalle.html, recibo.html
│   ├── caja/                # abrir.html, cerrar.html, estado.html, detalle.html, historial.html
│   ├── deudas/              # lista.html, form.html, detalle.html, reporte.html
│   ├── facturas/            # lista.html, form.html, detalle.html, reporte.html
│   ├── acreedores/          # lista.html, form.html
│   ├── gastos/              # lista.html, form.html
│   ├── reportes/            # stock.html, movimientos.html
│   ├── configuracion/       # form.html
│   ├── importar/            # index.html
│   ├── backup/              # index.html
│   ├── usuarios/            # lista.html, form.html (con selector de local para SUPERADMIN)
│   ├── perfil/              # index.html
│   ├── auditoria/           # lista.html
│   ├── locales/             # lista.html, form.html
│   ├── super/               # dashboard.html (metricas consolidadas)
│   ├── guia/                # index.html (ayuda contextual)
│   └── legal/               # index.html (terminos legales)
│
├── static/
│   ├── css/style.css        # Custom Bootstrap overrides + dark theme
│   ├── js/
│   │   ├── main.js          # Utilidades globales, sidebar, flash auto-dismiss
│   │   ├── dashboard.js     # Chart.js inicializacion (7 graficas)
│   │   ├── pos.js           # POS: carrito, busqueda, precio manual, pago
│   │   └── help.js          # Tour guiado de ayuda contextual
│   ├── vendor/
│   │   ├── bootstrap/       # bootstrap.min.css + bootstrap.bundle.min.js
│   │   ├── bootstrap-icons/  # bootstrap-icons.css + fonts/ (woff2, woff)
│   │   └── chartjs/         # chart.umd.min.js
│   └── uploads/
│       └── avatars/         # Fotos de perfil subidas
│
├── tests/                   # 24 archivos, 651 tests
│   ├── conftest.py          # 340+ LOC, 25+ fixtures (client, admin, superadmin, local, DB, etc.)
│   ├── test_auth.py         # Login, logout, sesion, permisos, SUPERADMIN
│   ├── test_productos.py    # CRUD productos
│   ├── test_categorias.py   # CRUD categorias + cascade
│   ├── test_proveedores.py  # CRUD proveedores
│   ├── test_clientes.py     # CRUD clientes
│   ├── test_inventario.py   # Entradas, salidas, stock
│   ├── test_ventas.py       # POS, venta completa, anulacion
│   ├── test_caja.py         # Apertura, cierre, movimientos
│   ├── test_deudas.py       # CRUD deudas + pagos
│   ├── test_facturas.py     # CRUD facturas + cobros
│   ├── test_gastos.py       # CRUD gastos
│   ├── test_usuarios.py     # CRUD usuarios + roles
│   ├── test_configuracion.py # Config del negocio
│   ├── test_dashboard.py    # Dashboard + filtros temporales
│   ├── test_backup.py       # Backup/restore
│   ├── test_busqueda.py     # Busqueda global escape
│   ├── test_acreedores.py   # CRUD acreedores
│   ├── test_auditoria.py    # Log auditoria + filtros
│   ├── test_importar.py     # Importacion Excel
│   ├── test_perfil.py       # Perfil usuario + avatar
│   ├── test_reportes.py     # Reportes stock + movimientos
│   ├── test_seed.py         # Seed: local default, admin, config
│   └── test_utils.py        # Utilidades, DB, templates, auth
│
├── .claude/commands/        # 14 skills para Claude Code
│   ├── test.md              # /test — ejecutar suite de tests
│   ├── feature.md           # /feature — flujo completo nueva feature
│   ├── fix.md               # /fix — diagnosticar y corregir bugs (TDD)
│   ├── status.md            # /status — reporte estado del proyecto
│   ├── build.md             # /build — construir instalador .exe
│   ├── review-code.md       # /review-code — review calidad/seguridad
│   ├── deploy.md            # /deploy — checklist pre-deploy
│   ├── refactor.md          # /refactor — reestructurar codigo sin cambiar comportamiento
│   ├── security.md          # /security — auditoria OWASP completa
│   ├── perf.md              # /perf — analisis de rendimiento y optimizacion
│   ├── migrate.md           # /migrate — crear migraciones de DB idempotentes
│   ├── coverage.md          # /coverage — analisis y mejora de cobertura de tests
│   ├── pr.md                # /pr — crear Pull Request profesional
│   └── audit.md             # /audit — barrido completo de salud del proyecto
│
├── installer/
│   └── techstock.iss        # Inno Setup script (Install/Repair/Uninstall)
│
├── .github/workflows/
│   └── ci.yml               # GitHub Actions: pytest en Python 3.10/3.11/3.12
│
├── techstock.spec           # PyInstaller spec (launcher.py entry point)
├── build_installer.bat      # Automatizacion: PyInstaller + PG portable + Inno Setup
├── Dockerfile               # python:3.11-slim + psycopg2
├── docker-compose.yml       # postgres:16-alpine + app web
├── requirements.txt         # 11 dependencias de produccion
├── requirements-dev.txt     # + pytest, httpx, pytest-cov
├── pytest.ini               # Config pytest + cobertura
├── .env.example             # Template de configuracion
└── .gitignore               # Python, venv, DB, IDE, dist, pgsql
```

---

## 4. Modelos de Datos (19 modelos, models.py)

### Diagrama de Relaciones

```
Local ──1:N──> (todas las tablas via local_id)

Usuario ──1:N──> AuditLog
Usuario ──1:N──> Venta (como vendedor)
Usuario ──1:N──> Caja
Usuario ──N:1──> Local (nullable para SUPERADMIN)

Categoria ──1:N──> Producto
Proveedor ──1:N──> Producto
Proveedor ──1:N──> MovimientoInventario
Proveedor ──1:N──> Deuda

Producto ──1:N──> MovimientoInventario
Producto ──1:N──> DetalleVenta

Cliente ──1:N──> Venta

Venta ──1:N──> DetalleVenta
Venta ──N:1──> Caja

Caja ──1:N──> MovimientoCaja
Caja ──1:N──> Venta

Acreedor ──1:N──> Deuda
Deuda ──1:N──> PagoDeuda

Factura ──1:N──> PagoFactura

Gasto (standalone, con local_id)
Configuracion (uno por local, unique local_id)
```

### Detalle de Modelos

| Modelo | Tabla | Campos clave | Soft Delete | Props Calculadas |
|--------|-------|--------------|-------------|------------------|
| **Local** | locales | nombre, codigo (unique), direccion, telefono, email, ciudad, responsable, activo | `activo` | — |
| **Usuario** | usuarios | username, password_hash, nombre_completo, email, telefono, foto, rol, permisos, local_id (nullable), activo | `activo` | — |
| **AuditLog** | audit_log | usuario_id, usuario_nombre, accion, entidad, entidad_id, detalle, ip_address, local_id | — | — |
| **Categoria** | categorias | nombre, descripcion, activo, local_id | `activo` | — |
| **Proveedor** | proveedores | nombre, contacto, telefono, email, direccion, nit_ruc, activo, local_id | `activo` | — |
| **Producto** | productos | codigo, referencia, nombre, descripcion, categoria_id, proveedor_id, precios (costo/venta/minimo), stock_actual, stock_minimo, unidad_medida, activo, local_id | `activo` | `margen`, `stock_bajo` |
| **MovimientoInventario** | movimientos_inventario | producto_id, tipo[ENTRADA/SALIDA/AJUSTE], cantidad, stock_anterior, stock_resultante, precio_unitario, proveedor_id, local_id | — | — |
| **Acreedor** | acreedores | nombre, tipo[PROVEEDOR/BANCO/PERSONA/OTRO], documento, telefono, email, direccion, notas, activo, local_id | `activo` | — |
| **Deuda** | deudas | concepto, acreedor_nombre, acreedor_tipo, acreedor_id, proveedor_id, monto_total, monto_pagado, fecha_deuda, fecha_vencimiento, estado, local_id | `estado=ANULADO` | `monto_pendiente`, `porcentaje_pagado`, `esta_vencida` |
| **PagoDeuda** | pagos_deuda | deuda_id, monto, fecha_pago, metodo_pago, comprobante, notas, local_id | — | — |
| **Factura** | facturas | numero_factura, cliente_nombre, cliente_documento, concepto, monto_total, monto_cobrado, fecha_emision, fecha_vencimiento, estado, local_id | `estado=ANULADO` | `monto_pendiente`, `porcentaje_cobrado`, `esta_vencida` |
| **PagoFactura** | cobros_factura | factura_id, monto, fecha_cobro, metodo_pago, comprobante, notas, local_id | — | — |
| **Gasto** | gastos | concepto, tipo[DIRECTO/INDIRECTO], categoria_gasto, monto, fecha, metodo_pago, comprobante, notas, activo, local_id | `activo` | — |
| **Configuracion** | configuracion | nombre_negocio, nit, direccion, telefono, email, moneda_simbolo, moneda_codigo, mensaje_recibo, pie_factura, local_id (unique) | — | — |
| **Cliente** | clientes | nombre, tipo_documento, documento, telefono, email, direccion, saldo_credito, activo, local_id | `activo` | — |
| **Venta** | ventas | numero_venta, cliente_id, cliente_nombre, vendedor_id, subtotal, descuento_total, impuesto_total, total, metodo_pago, monto_recibido, cambio, estado, caja_id, local_id | `estado=ANULADA` | `ganancia_total` |
| **DetalleVenta** | detalle_venta | venta_id, producto_id, producto_nombre, producto_codigo, cantidad, precio_unitario, precio_costo, descuento_item, subtotal, local_id | — | `ganancia` |
| **Caja** | cajas | usuario_id, numero_caja, monto_apertura, monto_cierre_esperado, monto_cierre_real, diferencia, estado[ABIERTA/CERRADA], local_id | — | `total_ingresos`, `total_egresos`, `saldo_esperado` |
| **MovimientoCaja** | movimientos_caja | caja_id, tipo[INGRESO/EGRESO], concepto, monto, referencia_tipo, referencia_id, local_id | — | — |

**Nota**: Todos los modelos (excepto Local) tienen `local_id = Column(Integer, ForeignKey("locales.id"))`.

---

## 5. Sistema de Autenticacion y Seguridad

### Flujo de Autenticacion

```
1. POST /login → auth_router.py → verify_password(bcrypt)
2. Cookie firmada: URLSafeTimedSerializer.dumps({user_id, username})
3. Cada request → AuthMiddleware → decode_session_cookie() → db.query(Usuario)
4. request.state.user = usuario activo
5. request.state.local_id = local efectivo (user.local_id o cookie SUPERADMIN)
6. Cookie expira en 8 horas (SESSION_MAX_AGE)
```

### Proteccion CSRF

```
1. Generacion: auth.py → generate_csrf_token(session_cookie[:16])
2. Template: {{ csrf_token(request) }} → <input hidden name="csrf_token">
3. Validacion: middleware.py → POST request → validate_csrf_token()
4. Exempciones: /ventas/api/* (JSON interno), TESTING=1
5. Token expira en 1 hora (CSRF_MAX_AGE)
```

### RBAC (Control de Acceso Basado en Roles)

| Rol | Modulos | Descripcion |
|-----|---------|-------------|
| **SUPERADMIN** | Todos + super_dashboard, locales, super_usuarios | Gestion global de todos los locales, sin local_id propio |
| **ADMIN** | Todos (14 modulos) | Acceso total dentro de su local |
| **VENDEDOR** | 11 modulos | dashboard, productos, ventas_pos, ventas_historial, clientes, caja, acreedores, deudas, facturas, gastos, reportes |
| **BODEGUERO** | 6 modulos | dashboard, productos, categorias, inventario, proveedores, reportes |

**SUPERADMIN**: `local_id=None`, gestiona todos los locales. Selecciona un local via cookie para operar dentro de el.

**Permisos custom**: Campo `permisos` en Usuario (comma-separated). Si esta vacio, usa permisos del rol.

### Funciones de Auth (auth.py)

| Funcion | Uso | Donde |
|---------|-----|-------|
| `require_auth` | Dependency — exige login | Todos los routers |
| `require_role("ADMIN")` | Dependency — exige rol (SUPERADMIN pasa cualquier check) | usuarios, configuracion |
| `require_superadmin` | Dependency — exige SUPERADMIN | locales, super_dashboard |
| `require_permiso("modulo")` | Dependency — exige acceso al modulo | Cada router |
| `get_local_id(request)` | Retorna local_id efectivo (user o cookie SUPERADMIN) | Todos los routers |
| `log_audit(db, user, accion, entidad, id, detalle, ip)` | Registra en audit_log con local_id | Todo CREATE/UPDATE/DELETE |
| `set_flash(response, msg, tipo)` | Flash message via cookie | Despues de cada accion |
| `get_flash(request)` | Lee y consume flash | _base_context() en main.py |
| `hash_password(plain)` | bcrypt hash | Crear/editar usuario |
| `verify_password(plain, hash)` | bcrypt verify | Login |
| `create_session_cookie(id, username)` | Cookie firmada | Login exitoso |
| `decode_session_cookie(cookie)` | Decodifica cookie | Middleware |
| `get_saved_accounts(request)` | Multi-cuenta | Login page |
| `user_has_permiso(user, modulo)` | Check permiso (SUPERADMIN/ADMIN → True siempre) | Templates + routers |
| `is_superadmin(user)` | Check si es SUPERADMIN | Templates (sidebar, navbar) |

### Infraestructura de Seguridad

- **CSRF obligatorio**: En TODO formulario `<form method="POST">` — `{{ csrf_token(request) }}`
- **Soft delete siempre**: `activo=False` para entidades, `estado="ANULADO"` para financieros
- **NUNCA usar `db.delete()`**: Siempre soft delete
- **Audit trail completo**: `log_audit()` en cada CREATE/UPDATE/DELETE de cada router
- **Transacciones atomicas**: ventas.py usa `try/except + db.rollback()` + `with_for_update()`
- **Cascade protection**: categorias solo se desactivan si no tienen productos activos
- **Thread-safe**: Serializer inicializado a nivel de modulo (no lazy singleton)
- **Cookie segura**: HttpOnly, SameSite=Lax, firmada con clave secreta en `.secret_key`
- **Multi-tenant isolation**: Todas las queries filtran por local_id

---

## 6. Convenciones de Codigo

### Python / Backend

- **Routers**: Un archivo por modulo en `routers/`, prefijo en espanol
- **Rutas estandar**: lista (GET), nuevo/nueva (GET+POST), editar (GET+POST), eliminar (POST), detalle (GET)
- **POST siempre**: `return RedirectResponse(url, status_code=303)` (patron PRG)
- **Auth en rutas**: `user: models.Usuario = Depends(require_permiso("modulo"))`
- **Multi-tenant en rutas**: `local_id = get_local_id(request)` al inicio de cada endpoint
- **Filtro local_id**: `if local_id is not None: query = query.filter(Model.local_id == local_id)`
- **Crear entidades**: Siempre setear `entity.local_id = local_id` antes de `db.add()`
- **Audit en mutaciones**: `log_audit(db, user, "CREATE", "entidad", entity.id, "detalle", request.client.host)`
- **Flash messages**: `set_flash(response, "Mensaje exitoso", "success")` o `?error=mensaje` en redirect
- **Errores al usuario**: Redirect con `?error=` o flash, NUNCA HTTP 500
- **Constantes compartidas**: Importar de `utils/constants.py`, no definir localmente
- **Queries reutilizables**: Importar de `utils/queries.py` (todas aceptan `local_id`)

### Templates (Jinja2)

- Todos extienden `base.html`
- Bloques: `title`, `page_title`, `content`, `scripts`
- Filtros disponibles: `{{ valor | moneda }}` (COP $), `{{ valor | numero }}` (separador miles)
- Globals: `{{ csrf_token(request) }}`, `{{ has_permiso(current_user, "modulo") }}`, `{{ is_superadmin(current_user) }}`
- CSRF: Obligatorio en todo `<form method="POST">`
- Assets: Solo rutas locales `/static/vendor/...`, NUNCA CDN
- Multi-tenant: `{{ current_local_name }}` disponible en contexto base

### Base de Datos

- **Soft delete**: `activo = Column(Boolean, default=True)` para entidades
- **Soft delete financiero**: `estado = Column(String, default="PENDIENTE")` → "ANULADO"
- **NUNCA `db.delete()`** — siempre soft delete
- **Timestamps**: `created_at = Column(DateTime, default=datetime.now)`, `updated_at` con `onupdate`
- **IDs**: Integer autoincremental
- **local_id**: `Column(Integer, ForeignKey("locales.id"))` en TODA tabla (excepto locales)
- **Unique compuestas**: Usar `UniqueConstraint("campo", "local_id", name="uq_tabla_campo_local")`
- **Migraciones**: Funciones idempotentes en `migrations.py` (sin Alembic)
- **PostgreSQL siempre**: database.py auto-configura pool_size=10, max_overflow=20
- **SQLite solo tests**: `DATABASE_URL=sqlite://` + `TESTING=1`

### Testing

- Archivos: `tests/test_<modulo>.py`
- Fixtures compartidas: `tests/conftest.py` (340+ LOC, 25+ fixtures)
- DB: SQLite in-memory con `StaticPool` (env: `DATABASE_URL=sqlite://`, `TESTING=1`)
- CSRF deshabilitado en tests (`TESTING=1` → middleware bypass)
- **Multi-tenant en tests**: Toda entidad creada en tests debe incluir `local_id=sample_local.id`
- Fixtures clave: `sample_local`, `admin_user` (con local), `superadmin_user` (sin local)
- CI: GitHub Actions en Python 3.10, 3.11, 3.12
- Config: `pytest.ini` con cobertura automatica y strict markers

---

## 7. Utilidades Compartidas (utils/)

### utils/constants.py
```python
METODOS_PAGO = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CHEQUE"]
METODOS_PAGO_VENTAS = ["EFECTIVO", "TARJETA", "TRANSFERENCIA", "CREDITO"]
TIPOS_ACREEDOR = ["PROVEEDOR", "BANCO", "PERSONA", "OTRO"]
TIPOS_GASTO = ["DIRECTO", "INDIRECTO"]
CATEGORIAS_GASTO = ["Arriendo", "Servicios publicos", "Nomina", ...]
```

### utils/financial.py
- `actualizar_estado_pago(entity, campo)` — Recalcula PENDIENTE/PARCIAL/PAGADO
- `siguiente_numero(db, model, campo, prefijo, local_id)` — Genera "FAC-0001" por local

### utils/queries.py
Todas aceptan `local_id: int = None`:
- `categorias_activas(db, local_id)`, `proveedores_activos(db, local_id)`
- `productos_activos(db, local_id)`, `productos_con_stock(db, local_id)`
- `clientes_activos(db, local_id)`, `vendedores_activos(db, local_id)`
- `acreedores_activos(db, local_id)`

### utils/dashboard.py
Funciones de metricas del dashboard, todas con filtro `local_id`.

### utils/pagination.py
- `paginate(query, page, per_page=20)` → `(items, total, total_pages)`

### utils/excel.py
- `generate_excel(title, headers, rows, col_widths, money_cols)` → `BytesIO` (.xlsx)

### utils/pdf.py
- Generacion de recibos y reportes PDF con ReportLab.

---

## 8. Dashboard (main.py → GET /)

El dashboard ejecuta 30+ queries con filtro temporal configurable (`fecha_desde`, `fecha_hasta`) y filtro por `local_id`:

- **SUPERADMIN sin local seleccionado**: Redirige a `/super` (dashboard consolidado)
- **SUPERADMIN con local seleccionado**: Ve dashboard del local seleccionado
- **Usuarios normales**: Ven dashboard de su local

### Super Dashboard (/super)
Dashboard exclusivo SUPERADMIN con metricas globales:
- Total locales activos, usuarios, productos, ventas
- Tabla por local: usuarios, productos, ventas hoy/mes, stock bajo, deudas pendientes

### Dashboard de Local (/)
- Productos activos, proveedores, categorias (filtrados por local)
- Stock bajo, valor inventario
- Ventas y ganancias del periodo
- Deudas y facturas pendientes/vencidas
- 7 graficas Chart.js

---

## 9. Migraciones (migrations.py)

Sin Alembic. Cada migracion es una funcion idempotente que verifica antes de ejecutar:

```python
if table_exists(conn, "tabla"):
    columns = get_table_columns(conn, "tabla")
    if "columna" not in columns:
        conn.execute(text("ALTER TABLE tabla ADD COLUMN columna TIPO DEFAULT valor"))
```

### Migraciones existentes
1. `facturas.cliente_id` — FK a clientes
2. `movimientos_inventario.venta_id` — FK a ventas
3. `acreedores` — Tabla completa
4. `productos.referencia` — Campo referencia
5. `productos.precio_venta_minimo` — Precio minimo
6. `detalle_venta.precio_costo` — Costo al momento de venta
7. `deudas.acreedor_id` — FK a acreedores
8. `usuarios.email` — Email del usuario
9. `usuarios.telefono` — Telefono del usuario
10. `usuarios.foto` — Foto de perfil
11. `usuarios.permisos` — Permisos custom
12. `categorias.activo` — Soft delete
13. **Multi-tenant** — Crea tabla `locales`, agrega `local_id` a todas las tablas, backfill al local default, unique constraints compuestas, upgrade primer admin a SUPERADMIN

**Regla**: SQLite (tests) retorna 0 migraciones — `create_all()` maneja el schema completo.

---

## 10. Seed (seed.py)

Ejecutado al iniciar `main.py` (no en tests). Idempotente — solo crea si la tabla esta vacia.

1. **Local default**: Crea "Sede Principal" (codigo: SEDE-001) si no existen locales
2. **SUPERADMIN**: Crea usuario con `rol="SUPERADMIN"`, `local_id=None`. Lee credenciales de env (`ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_NAME`). Si no hay password, genera una segura y la muestra en consola.
3. **Configuracion**: Crea registro para el local default con nombre "TechStock", moneda COP

---

## 11. Middleware (middleware.py)

### AuthMiddleware
1. Rutas publicas: `/login`, `/favicon.ico`, `/static/*` → sin auth
2. Cookie de sesion: Decodifica → busca usuario activo en DB → `request.state.user`
3. **Multi-tenant**: Inyecta `request.state.local_id` y `request.state.selected_local_id`
   - SUPERADMIN: Lee cookie `techstock_selected_local` → `selected_local_id`
   - No-SUPERADMIN: Usa `user.local_id`
4. CSRF en POST: Valida `csrf_token` del form contra la cookie de sesion
5. Exempciones CSRF: `/ventas/api/*` (endpoints JSON del POS)
6. Tests: `TESTING=1` desactiva validacion CSRF

---

## 12. Launcher GUI (launcher.py)

Interfaz tkinter dark-theme para gestionar PostgreSQL portable + servidor web.

### Flujo de inicio (`_start_all()`)
1. Verificar si existe `pgsql/bin/pg_ctl.exe` (PG portable)
2. Si existe: `initdb` → `pg_ctl start` → crear usuario/DB
3. Configurar `DATABASE_URL` en env
4. Verificar conexion a DB
5. Iniciar `main.py` como subprocess
6. Monitorear stdout en thread separado
7. Esperar `http://localhost:8000` responda (30 intentos)

### Constantes
- Puerto web: **8000**
- Puerto PostgreSQL: **5433** (evita conflicto con PG instalado en 5432)
- Datos: `%APPDATA%/TechStock/pgdata`
- Log PG: `%APPDATA%/TechStock/pg.log`

---

## 13. Deploy

### Opcion 1: Docker Compose
```bash
docker-compose up -d          # PostgreSQL 16 + app en :8000
docker-compose down            # Detener
docker-compose logs -f web     # Ver logs
```

### Opcion 2: Instalador Windows (.exe)
```bash
build_installer.bat            # Genera dist/installer/TechStock_Setup_v3.0.exe
```
Incluye: app empaquetada + PostgreSQL 16 portable + Inno Setup installer.

### Opcion 3: Desarrollo directo
```bash
pip install -r requirements.txt
python main.py                 # http://localhost:8000
```

---

## 14. Comandos de Desarrollo

```bash
# ── Servidor ──
python main.py                            # Dev server en 0.0.0.0:8000

# ── Dependencias ──
pip install -r requirements.txt           # Produccion
pip install -r requirements-dev.txt       # + pytest, httpx, coverage

# ── Tests ──
pytest                                    # Todos (651 tests, con cobertura)
pytest tests/test_ventas.py -v            # Modulo especifico
pytest --tb=short -q                      # Resumen corto
pytest -k "test_crear_venta"              # Test especifico
pytest --cov --cov-report=html            # Cobertura HTML en htmlcov/

# ── Build ──
build_installer.bat                       # PyInstaller + PG portable + Inno Setup
pyinstaller techstock.spec --clean        # Solo PyInstaller

# ── Docker ──
docker-compose up -d                      # PostgreSQL + app
docker-compose down                       # Detener
```

---

## 15. Skills para Claude Code (.claude/commands/)

### Uso
Invocar desde la terminal de Claude Code con `/<skill> [argumentos]`.

14 skills organizados por rol del equipo de desarrollo:

#### Desarrollo (implementacion de funcionalidad)
| Skill | Invocacion | Rol | Descripcion |
|-------|-----------|-----|-------------|
| `/feature` | `/feature modulo de notificaciones` | Feature Developer | Flujo completo: analisis → modelo → router → template → test |
| `/fix` | `/fix busqueda retorna 422` | Bug Fixer | TDD: test que falla → fix minimo → verificacion |
| `/migrate` | `/migrate agregar campo email a proveedores` | DB Specialist | Crear migracion idempotente para PostgreSQL |
| `/refactor` | `/refactor extraer logica de ventas a utils` | Refactoring Lead | Reestructurar sin cambiar comportamiento |

#### Calidad y seguridad (verificacion)
| Skill | Invocacion | Rol | Descripcion |
|-------|-----------|-----|-------------|
| `/test` | `/test`, `/test ventas`, `/test fix` | QA Engineer | Ejecuta tests; con `fix` corrige fallos |
| `/coverage` | `/coverage`, `/coverage ventas` | QA Analyst | Analiza brechas de cobertura y genera tests |
| `/review-code` | `/review-code`, `/review-code ventas.py` | Code Reviewer | Review: seguridad, calidad, consistencia |
| `/security` | `/security`, `/security auth.py` | Security Auditor | Auditoria OWASP completa del proyecto |
| `/perf` | `/perf`, `/perf dashboard` | Performance Engineer | Analisis N+1, queries lentas, optimizaciones |

#### Operaciones (build, deploy, estado)
| Skill | Invocacion | Rol | Descripcion |
|-------|-----------|-----|-------------|
| `/status` | `/status` | Project Manager | Reporte: git, tests, conteo de codigo, issues |
| `/audit` | `/audit` | Tech Lead | Barrido exhaustivo: codigo, tests, seguridad, deuda tecnica |
| `/build` | `/build`, `/build clean` | Build Engineer | Construye instalador .exe (PyInstaller + Inno Setup) |
| `/deploy` | `/deploy docker`, `/deploy windows` | DevOps | Checklist pre-deploy |
| `/pr` | `/pr`, `/pr feat/nueva-feature` | Release Manager | Crear Pull Request profesional con validaciones |

### Flujo recomendado por tipo de trabajo

**Nueva feature**: `/feature` → `/test` → `/review-code` → `/pr`
**Corregir bug**: `/fix` → `/test` → `/pr`
**Optimizar**: `/perf` → `/refactor` → `/test` → `/pr`
**Pre-release**: `/audit` → `/security` → `/coverage` → `/deploy` → `/build`
**Mantenimiento**: `/status` → `/coverage` → `/refactor` → `/test`

---

## 16. Patron CRUD Estandar (para nuevos modulos)

### Router (routers/<modulo>.py)
```python
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
from auth import require_permiso, log_audit, set_flash, get_local_id
import models

router = APIRouter(prefix="/<modulo>", tags=["<Modulo>"])

@router.get("")                        # Lista con filtro local_id
@router.get("/nuevo")                  # Form crear (GET)
@router.post("/nuevo")                 # Guardar nuevo (con local_id) → redirect 303
@router.get("/{id}/detalle")           # Ver detalle (filtrado por local_id)
@router.get("/{id}/editar")            # Form editar (GET, filtrado)
@router.post("/{id}/editar")           # Guardar edicion → redirect 303
@router.post("/{id}/eliminar")         # Soft delete → redirect 303
```

### Checklist nuevo modulo
1. Modelo en `models.py` con `activo = Column(Boolean, default=True)` y `local_id = Column(Integer, ForeignKey("locales.id"))`
2. Migracion en `migrations.py` (idempotente, solo PostgreSQL)
3. Router en `routers/<modulo>.py` con `get_local_id` + `require_permiso` + `log_audit` + CSRF
4. **Todas las queries filtran por local_id**
5. **Todas las entidades creadas setean local_id**
6. Templates en `templates/<modulo>/`
7. Enlace en sidebar de `templates/base.html`
8. Modulo en `auth.py` → `MODULOS_DISPONIBLES` + `PERMISOS_POR_ROL`
9. Router registrado en `main.py` (`app.include_router`)
10. Tests en `tests/test_<modulo>.py` + fixtures en `conftest.py` (con `sample_local`)
11. Constantes compartidas en `utils/constants.py` si aplica

---

## 17. Configuracion de Base de Datos (database.py)

### Logica de conexion
```
1. Carga .env (sin python-dotenv, parsing manual)
2. Si DATABASE_URL en env → usarla
3. Si no → "postgresql://techstock:techstock@localhost:5433/techstock"
4. Si empieza con "postgresql" → pool_size=10, max_overflow=20, client_encoding=utf8
5. Si empieza con "sqlite" → check_same_thread=False, StaticPool si in-memory
```

---

## 18. Backup System (routers/backup.py)

### Tablas incluidas en backup
locales, usuarios, categorias, productos, proveedores, clientes, ventas, detalle_venta, movimientos_inventario, cajas, movimientos_caja, deudas, pagos_deuda, facturas, cobros_factura, acreedores, gastos, configuracion, audit_log

### Formato
Backup SQL (INSERT statements) generado por query directa o pg_dump. Restore ejecuta los INSERTs via psql o SQLAlchemy fallback.

---

## 19. Roadmap

### Completado (v1.0 → v3.0)
- CRUD completo: productos, categorias, proveedores, clientes, inventario, ventas
- POS con precio manual editable, ganancias visibles, busqueda por referencia
- Caja: apertura, cierre, movimientos, historial
- Deudas (cuentas por pagar) + pagos parciales
- Facturas (cuentas por cobrar) + cobros parciales + importacion Excel
- Acreedores con tipos (proveedor, banco, persona, otro)
- Modulo de Gastos completo (CRUD + filtros + categorias)
- Dashboard con 7 graficas + filtro temporal (fecha_desde/fecha_hasta)
- Importacion Excel (categorias, productos, facturas)
- Exportacion Excel en reportes
- Generacion PDF de recibos
- Auditoria completa con filtros
- Perfiles de usuario + avatar
- Backup/Restore de base de datos
- Sistema RBAC (SUPERADMIN, ADMIN, VENDEDOR, BODEGUERO) + permisos custom
- CSRF en todos los formularios, soft delete everywhere, audit trail completo
- Instalador Windows .exe (PyInstaller + Inno Setup + PostgreSQL portable)
- Assets 100% offline (Bootstrap, Icons, Chart.js locales)
- **Multi-tenant completo (v3.0)**: Modelo Local, SUPERADMIN, filtro local_id en todos los routers, dashboard consolidado, seleccion de local por cookie, unique constraints compuestas, numeros correlativos por local
- **14 skills de desarrollo profesional** para Claude Code

### Pendiente
1. **Tests para locales/super_dashboard** — Nuevos routers multi-tenant con baja cobertura
2. **Rate limiting** — En endpoints publicos (login)
3. **Image resizing** — Para avatars de perfil
4. **Notificaciones** — Stock bajo, deudas vencidas (alertas en dashboard)
5. **Multi-idioma** — Soporte i18n (español base, ingles opcional)
6. **API REST** — Endpoints JSON para integraciones externas
7. **Reportes avanzados** — Comparativos entre locales (SUPERADMIN)
