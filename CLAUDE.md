# TechStock v2.0 — Guia Completa de Desarrollo

## Inicio Rapido (Orientacion Autonoma)

Al iniciar una nueva sesion, NO investigues el proyecto desde cero. Este documento tiene todo lo necesario.

- **Stack**: FastAPI 0.115 + SQLAlchemy 2.0 + PostgreSQL 16 + Jinja2 + Bootstrap 5.3 (SSR)
- **Tests**: `pytest --tb=short -q` (258 tests, 58% cobertura)
- **Dev server**: `python main.py` (0.0.0.0:8000, requiere PostgreSQL activo)
- **Skills disponibles**: `/test`, `/feature`, `/fix`, `/status`, `/build`, `/review-code`, `/deploy`
- **Idioma del codigo**: Nombres de rutas, variables y UI en espanol. Comentarios y docstrings en espanol.

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

---

## 2. Estructura del Proyecto

```
inventario-tech/
├── main.py                  # App FastAPI, dashboard (30+ queries), startup, registro de routers
├── database.py              # Engine, SessionLocal, Base, get_db (PG/SQLite auto)
├── models.py                # 17 modelos SQLAlchemy (441 LOC)
├── auth.py                  # Hash, cookies, sesion, CSRF, audit, permisos, RBAC (250 LOC)
├── middleware.py             # AuthMiddleware: cookie → request.state.user + CSRF POST
├── templates_config.py      # Jinja2 config + filtros (moneda, numero) + csrf_token global
├── seed.py                  # Admin inicial + config default (idempotente)
├── migrations.py            # 12 migraciones idempotentes (sin Alembic, PostgreSQL only)
├── launcher.py              # GUI tkinter dark-theme: PG portable + server lifecycle (666 LOC)
│
├── utils/
│   ├── __init__.py
│   ├── constants.py         # METODOS_PAGO, TIPOS_ACREEDOR, CATEGORIAS_GASTO
│   ├── financial.py         # actualizar_estado_pago(), siguiente_numero()
│   ├── pagination.py        # paginate(query, page, per_page) → (items, total, pages)
│   └── excel.py             # generate_excel(title, headers, rows, ...) → BytesIO
│
├── routers/                 # 19 routers, 128+ endpoints
│   ├── __init__.py
│   ├── auth_router.py       # Login, logout, switch account (5 endpoints)
│   ├── usuarios.py          # CRUD usuarios + permisos (6 endpoints)
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
│   ├── configuracion.py     # Config negocio (nombre, moneda, recibo) (3 endpoints)
│   ├── importar.py          # Import Excel categorias/productos/facturas (3 endpoints)
│   ├── backup.py            # Backup/restore DB completo (7 endpoints)
│   ├── perfil.py            # Perfil usuario + avatar (5 endpoints)
│   └── auditoria.py         # Log de auditoria con filtros (1 endpoint)
│
├── templates/               # 47 HTML templates
│   ├── base.html            # Layout maestro: sidebar, navbar, Bootstrap, flash messages
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
│   ├── usuarios/            # lista.html, form.html
│   ├── perfil/              # index.html
│   ├── auditoria/           # lista.html
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
├── tests/                   # 17 archivos, 258 tests
│   ├── conftest.py          # 264 LOC, 20+ fixtures (client, admin, DB, productos, etc.)
│   ├── test_auth.py         # Login, logout, sesion, permisos
│   ├── test_productos.py    # CRUD productos
│   ├── test_categorias.py   # CRUD categorias + cascade
│   ├── test_proveedores.py  # CRUD proveedores
│   ├── test_clientes.py     # CRUD clientes
│   ├── test_inventario.py   # Entradas, salidas, stock
│   ├── test_ventas.py       # POS, venta completa, anulacion
│   ├── test_caja.py         # Apertura, cierre, movimientos
│   ├── test_deudas.py       # CRUD deudas + pagos
│   ├── test_facturas.py     # CRUD facturas + cobros
│   ├── test_gastos.py       # CRUD gastos (12 tests)
│   ├── test_usuarios.py     # CRUD usuarios + roles
│   ├── test_configuracion.py # Config del negocio
│   ├── test_dashboard.py    # Dashboard + filtros temporales
│   ├── test_backup.py       # Backup/restore
│   └── test_busqueda.py     # Busqueda global escape
│
├── .claude/commands/        # 7 skills para Claude Code
│   ├── test.md              # /test — ejecutar suite de tests
│   ├── feature.md           # /feature — flujo completo nueva feature
│   ├── fix.md               # /fix — diagnosticar y corregir bugs (TDD)
│   ├── status.md            # /status — reporte estado del proyecto
│   ├── build.md             # /build — construir instalador .exe
│   ├── review-code.md       # /review-code — review calidad/seguridad
│   └── deploy.md            # /deploy — checklist pre-deploy
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

## 3. Modelos de Datos (17 modelos, models.py)

### Diagrama de Relaciones

```
Usuario ──1:N──> AuditLog
Usuario ──1:N──> Venta (como vendedor)
Usuario ──1:N──> Caja

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

Gasto (standalone)
Configuracion (singleton)
```

### Detalle de Modelos

| Modelo | Tabla | Campos | Soft Delete | Props Calculadas |
|--------|-------|--------|-------------|------------------|
| **Usuario** | usuarios | 12 (username, password_hash, nombre_completo, email, telefono, foto, rol, permisos, activo, ultimo_login, created_at, updated_at) | `activo` | — |
| **AuditLog** | audit_log | 8 (usuario_id, usuario_nombre, accion, entidad, entidad_id, detalle, ip_address, created_at) | — | — |
| **Categoria** | categorias | 5 (nombre, descripcion, activo, created_at) | `activo` | — |
| **Proveedor** | proveedores | 8 (nombre, contacto, telefono, email, direccion, nit_ruc, activo, created_at) | `activo` | — |
| **Producto** | productos | 14 (codigo, referencia, nombre, descripcion, categoria_id, proveedor_id, precio_costo, precio_venta, precio_venta_minimo, stock_actual, stock_minimo, unidad_medida, activo, timestamps) | `activo` | `margen`, `stock_bajo` |
| **MovimientoInventario** | movimientos_inventario | 10 (producto_id, tipo[ENTRADA/SALIDA/AJUSTE], cantidad, stock_anterior, stock_resultante, precio_unitario, proveedor_id, numero_referencia, observaciones, fecha) | — | — |
| **Acreedor** | acreedores | 10 (nombre, tipo[PROVEEDOR/BANCO/PERSONA/OTRO], documento, telefono, email, direccion, notas, activo, timestamps) | `activo` | — |
| **Deuda** | deudas | 11 (concepto, acreedor_nombre, acreedor_tipo, acreedor_id, proveedor_id, monto_total, monto_pagado, fecha_deuda, fecha_vencimiento, estado, notas) | `estado=ANULADO` | `monto_pendiente`, `porcentaje_pagado`, `esta_vencida` |
| **PagoDeuda** | pagos_deuda | 7 (deuda_id, monto, fecha_pago, metodo_pago, comprobante, notas, created_at) | — | — |
| **Factura** | facturas | 12 (numero_factura, cliente_nombre, cliente_documento, cliente_telefono, cliente_email, concepto, monto_total, monto_cobrado, fecha_emision, fecha_vencimiento, estado, notas) | `estado=ANULADO` | `monto_pendiente`, `porcentaje_cobrado`, `esta_vencida` |
| **PagoFactura** | cobros_factura | 7 (factura_id, monto, fecha_cobro, metodo_pago, comprobante, notas, created_at) | — | — |
| **Gasto** | gastos | 10 (concepto, tipo[DIRECTO/INDIRECTO], categoria_gasto, monto, fecha, metodo_pago, comprobante, notas, activo, timestamps) | `activo` | — |
| **Configuracion** | configuracion | 12 (nombre_negocio, nit, direccion, telefono, email, logo_path, moneda_simbolo, moneda_codigo, mensaje_recibo, pie_factura, timestamps) | — | — |
| **Cliente** | clientes | 10 (nombre, tipo_documento[CC/NIT/CE/PASAPORTE], documento, telefono, email, direccion, notas, saldo_credito, activo, timestamps) | `activo` | — |
| **Venta** | ventas | 14 (numero_venta, cliente_id, cliente_nombre, vendedor_id, subtotal, descuento_total, impuesto_total, total, metodo_pago, monto_recibido, cambio, estado, notas, caja_id, fecha) | `estado=ANULADA` | `ganancia_total` |
| **DetalleVenta** | detalle_venta | 10 (venta_id, producto_id, producto_nombre, producto_codigo, cantidad, precio_unitario, precio_costo, descuento_item, subtotal) | — | `ganancia` |
| **Caja** | cajas | 10 (usuario_id, numero_caja, monto_apertura, monto_cierre_esperado, monto_cierre_real, diferencia, estado[ABIERTA/CERRADA], fecha_apertura, fecha_cierre, notas_cierre) | — | `total_ingresos`, `total_egresos`, `saldo_esperado` |
| **MovimientoCaja** | movimientos_caja | 7 (caja_id, tipo[INGRESO/EGRESO], concepto, monto, referencia_tipo, referencia_id, created_at) | — | — |

---

## 4. Sistema de Autenticacion y Seguridad

### Flujo de Autenticacion

```
1. POST /login → auth_router.py → verify_password(bcrypt)
2. Cookie firmada: URLSafeTimedSerializer.dumps({user_id, username})
3. Cada request → AuthMiddleware → decode_session_cookie() → db.query(Usuario)
4. request.state.user = usuario activo
5. Cookie expira en 8 horas (SESSION_MAX_AGE)
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
| **ADMIN** | Todos (14 modulos) | Acceso total al sistema |
| **VENDEDOR** | 11 modulos | dashboard, productos, ventas_pos, ventas_historial, clientes, caja, acreedores, deudas, facturas, gastos, reportes |
| **BODEGUERO** | 6 modulos | dashboard, productos, categorias, inventario, proveedores, reportes |

**Permisos custom**: Campo `permisos` en Usuario (comma-separated). Si esta vacio, usa permisos del rol.

### Funciones de Auth (auth.py)

| Funcion | Uso | Donde |
|---------|-----|-------|
| `require_auth` | Dependency — exige login | Todos los routers |
| `require_role("ADMIN")` | Dependency — exige rol | usuarios, configuracion |
| `require_permiso("modulo")` | Dependency — exige acceso al modulo | Cada router |
| `log_audit(db, user, accion, entidad, id, detalle, ip)` | Registra en audit_log | Todo CREATE/UPDATE/DELETE |
| `set_flash(response, msg, tipo)` | Flash message via cookie | Despues de cada accion |
| `get_flash(request)` | Lee y consume flash | _base_context() en main.py |
| `hash_password(plain)` | bcrypt hash | Crear/editar usuario |
| `verify_password(plain, hash)` | bcrypt verify | Login |
| `create_session_cookie(id, username)` | Cookie firmada | Login exitoso |
| `decode_session_cookie(cookie)` | Decodifica cookie | Middleware |
| `get_saved_accounts(request)` | Multi-cuenta | Login page |
| `user_has_permiso(user, modulo)` | Check permiso | Templates + routers |

### Infraestructura de Seguridad

- **CSRF obligatorio**: En TODO formulario `<form method="POST">` — `{{ csrf_token(request) }}`
- **Soft delete siempre**: `activo=False` para entidades, `estado="ANULADO"` para financieros
- **NUNCA usar `db.delete()`**: Siempre soft delete
- **Audit trail completo**: `log_audit()` en cada CREATE/UPDATE/DELETE de cada router
- **Transacciones atomicas**: ventas.py usa `try/except + db.rollback()` + `with_for_update()`
- **Cascade protection**: categorias solo se desactivan si no tienen productos activos
- **Thread-safe**: Serializer inicializado a nivel de modulo (no lazy singleton)
- **Cookie segura**: HttpOnly, SameSite=Lax, firmada con clave secreta en `.secret_key`

---

## 5. Convenciones de Codigo

### Python / Backend

- **Routers**: Un archivo por modulo en `routers/`, prefijo en espanol
- **Rutas estandar**: lista (GET), nuevo/nueva (GET+POST), editar (GET+POST), eliminar (POST), detalle (GET)
- **POST siempre**: `return RedirectResponse(url, status_code=303)` (patron PRG)
- **Auth en rutas**: `user: models.Usuario = Depends(require_permiso("modulo"))`
- **Audit en mutaciones**: `log_audit(db, user, "CREATE", "entidad", entity.id, "detalle", request.client.host)`
- **Flash messages**: `set_flash(response, "Mensaje exitoso", "success")` o `?error=mensaje` en redirect
- **Errores al usuario**: Redirect con `?error=` o flash, NUNCA HTTP 500
- **Constantes compartidas**: Importar de `utils/constants.py`, no definir localmente

### Templates (Jinja2)

- Todos extienden `base.html`
- Bloques: `title`, `page_title`, `content`, `scripts`
- Filtros disponibles: `{{ valor | moneda }}` (COP $), `{{ valor | numero }}` (separador miles)
- Globals: `{{ csrf_token(request) }}`, `{{ has_permiso(current_user, "modulo") }}`
- CSRF: Obligatorio en todo `<form method="POST">`
- Assets: Solo rutas locales `/static/vendor/...`, NUNCA CDN

### Base de Datos

- **Soft delete**: `activo = Column(Boolean, default=True)` para entidades
- **Soft delete financiero**: `estado = Column(String, default="PENDIENTE")` → "ANULADO"
- **NUNCA `db.delete()`** — siempre soft delete
- **Timestamps**: `created_at = Column(DateTime, default=datetime.now)`, `updated_at` con `onupdate`
- **IDs**: Integer autoincremental
- **Migraciones**: Funciones idempotentes en `migrations.py` (sin Alembic)
- **PostgreSQL siempre**: database.py auto-configura pool_size=10, max_overflow=20
- **SQLite solo tests**: `DATABASE_URL=sqlite://` + `TESTING=1`

### Testing

- Archivos: `tests/test_<modulo>.py`
- Fixtures compartidas: `tests/conftest.py` (264 LOC, 20+ fixtures)
- DB: SQLite in-memory con `StaticPool` (env: `DATABASE_URL=sqlite://`, `TESTING=1`)
- CSRF deshabilitado en tests (`TESTING=1` → middleware bypass)
- CI: GitHub Actions en Python 3.10, 3.11, 3.12
- Config: `pytest.ini` con cobertura automatica y strict markers

---

## 6. Utilidades Compartidas (utils/)

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
- `siguiente_numero(db, model, campo, prefijo)` — Genera "FAC-0001", "VTA-0002", etc.

### utils/pagination.py
- `paginate(query, page, per_page=20)` → `(items, total, total_pages)`

### utils/excel.py
- `generate_excel(title, headers, rows, col_widths, money_cols)` → `BytesIO` (.xlsx)

---

## 7. Dashboard (main.py → GET /)

El dashboard ejecuta 30+ queries con filtro temporal configurable (`fecha_desde`, `fecha_hasta`):

### Metricas calculadas
- Productos activos, proveedores, categorias
- Stock bajo (productos donde `stock_actual <= stock_minimo`)
- Valor total del inventario (`SUM(stock * precio_costo)`)
- Ventas del periodo (total $ y cantidad)
- Ganancia del periodo (`SUM(subtotal - precio_costo * cantidad)`)
- Deudas pendientes y vencidas
- Facturas por cobrar y vencidas

### Graficas Chart.js (7)
1. Ventas ultimos 7 dias (barras)
2. Movimientos: entradas vs salidas (barras agrupadas)
3. Valor inventario por categoria (doughnut)
4. Estado deudas: pendiente/parcial/pagado (doughnut)
5. Estado facturas: pendiente/parcial/pagado (doughnut)
6. Top 5 productos mas vendidos (tabla)
7. Productos con stock bajo (tabla)

---

## 8. Migraciones (migrations.py)

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

**Regla**: SQLite (tests) retorna 0 migraciones — `create_all()` maneja el schema completo.

---

## 9. Seed (seed.py)

Ejecutado al iniciar `main.py` (no en tests). Idempotente — solo crea si la tabla esta vacia.

1. **Admin**: Lee `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_NAME` de env (default: admin/admin123/Administrador)
2. **Configuracion**: Crea registro singleton con nombre "TechStock", moneda COP

---

## 10. Middleware (middleware.py)

### AuthMiddleware
1. Rutas publicas: `/login`, `/favicon.ico`, `/static/*` → sin auth
2. Cookie de sesion: Decodifica → busca usuario activo en DB → `request.state.user`
3. CSRF en POST: Valida `csrf_token` del form contra la cookie de sesion
4. Exempciones CSRF: `/ventas/api/*` (endpoints JSON del POS)
5. Tests: `TESTING=1` desactiva validacion CSRF

---

## 11. Launcher GUI (launcher.py)

Interfaz tkinter dark-theme para gestionar PostgreSQL portable + servidor web.

### Flujo de inicio (`_start_all()`)
1. Verificar si existe `pgsql/bin/pg_ctl.exe` (PG portable)
2. Si existe: `initdb` → `pg_ctl start` → crear usuario/DB
3. Configurar `DATABASE_URL` en env
4. Verificar conexion a DB
5. Iniciar `main.py` como subprocess
6. Monitorear stdout en thread separado
7. Esperar `http://localhost:8000` responda (30 intentos)

### Flujo de parada (`_stop_all()`)
1. `process.terminate()` → `wait(5)` → `kill()` si no termina
2. `pg_ctl stop -m fast -w -t 15`

### Constantes
- Puerto web: **8000**
- Puerto PostgreSQL: **5433** (evita conflicto con PG instalado en 5432)
- Datos: `%APPDATA%/TechStock/pgdata`
- Log PG: `%APPDATA%/TechStock/pg.log`

---

## 12. Deploy

### Opcion 1: Docker Compose
```bash
docker-compose up -d          # PostgreSQL 16 + app en :8000
docker-compose down            # Detener
docker-compose logs -f web     # Ver logs
```

### Opcion 2: Instalador Windows (.exe)
```bash
build_installer.bat            # Genera dist/installer/TechStock_Setup_v2.0.exe
```
Incluye: app empaquetada + PostgreSQL 16 portable + Inno Setup installer.
El instalador soporta: Instalar / Reparar / Desinstalar.

### Opcion 3: Desarrollo directo
```bash
pip install -r requirements.txt
# Tener PostgreSQL corriendo en localhost:5433 (o configurar .env)
python main.py                 # http://localhost:8000
```

---

## 13. Comandos de Desarrollo

```bash
# ── Servidor ──
python main.py                            # Dev server en 0.0.0.0:8000

# ── Dependencias ──
pip install -r requirements.txt           # Produccion
pip install -r requirements-dev.txt       # + pytest, httpx, coverage

# ── Tests ──
pytest                                    # Todos (258 tests, con cobertura)
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

## 14. Skills para Claude Code (.claude/commands/)

### Uso
Invocar desde la terminal de Claude Code con `/<skill> [argumentos]`.

| Skill | Invocacion | Descripcion |
|-------|-----------|-------------|
| `/test` | `/test`, `/test ventas`, `/test --cov`, `/test fix` | Ejecuta tests; con `fix` corrige fallos automaticamente |
| `/feature` | `/feature modulo de notificaciones` | Flujo completo: analisis → modelo → router → template → test |
| `/fix` | `/fix busqueda retorna 422` | TDD: test que falla → fix minimo → verificacion |
| `/status` | `/status` | Reporte: git, tests, conteo de codigo, issues |
| `/build` | `/build`, `/build clean` | Construye instalador .exe (PyInstaller + Inno Setup) |
| `/review-code` | `/review-code`, `/review-code ventas.py` | Review: seguridad, calidad, consistencia |
| `/deploy` | `/deploy docker`, `/deploy windows` | Checklist pre-deploy |

### Flujo de /feature (el mas completo)
1. **Analisis**: Lee CLAUDE.md, investiga codigo relacionado con Explore agent
2. **Implementacion** (en orden): Modelo → Migracion → Router → Templates → Sidebar → Auth → Main
3. **Testing**: Tests en `tests/test_<modulo>.py` + fixtures en `conftest.py`
4. **Verificacion**: /simplify, CSRF, audit, soft delete

### Flujo de /fix (TDD)
1. **Diagnostico**: Explore agent para encontrar causa raiz
2. **Test primero**: Escribir test que reproduce el bug (debe fallar)
3. **Fix minimo**: Solo lo necesario, sin refactors
4. **Verificacion**: pytest completo verde

---

## 15. Patron CRUD Estandar (para nuevos modulos)

### Router (routers/<modulo>.py)
```python
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
from auth import require_permiso, log_audit, set_flash
import models

router = APIRouter(prefix="/<modulo>", tags=["<Modulo>"])

@router.get("")                        # Lista con busqueda/filtros/paginacion
@router.get("/nuevo")                  # Form crear (GET)
@router.post("/nuevo")                 # Guardar nuevo → redirect 303
@router.get("/{id}/detalle")           # Ver detalle
@router.get("/{id}/editar")            # Form editar (GET)
@router.post("/{id}/editar")           # Guardar edicion → redirect 303
@router.post("/{id}/eliminar")         # Soft delete → redirect 303
```

### Template (templates/<modulo>/lista.html)
```html
{% extends "base.html" %}
{% block title %}Titulo{% endblock %}
{% block page_title %}Titulo Pagina{% endblock %}
{% block content %}
  <!-- Tabla, filtros, paginacion -->
{% endblock %}
{% block scripts %}
  <!-- JS especifico del modulo -->
{% endblock %}
```

### Checklist nuevo modulo
1. Modelo en `models.py` con `activo = Column(Boolean, default=True)`
2. Migracion en `migrations.py` (idempotente, solo PostgreSQL)
3. Router en `routers/<modulo>.py` con `require_permiso` + `log_audit` + CSRF
4. Templates en `templates/<modulo>/`
5. Enlace en sidebar de `templates/base.html`
6. Modulo en `auth.py` → `MODULOS_DISPONIBLES` + `PERMISOS_POR_ROL`
7. Router registrado en `main.py` (`app.include_router`)
8. Tests en `tests/test_<modulo>.py` + fixtures en `conftest.py`
9. Constantes compartidas en `utils/constants.py` si aplica

---

## 16. Configuracion de Base de Datos (database.py)

### Logica de conexion
```
1. Carga .env (sin python-dotenv, parsing manual)
2. Si DATABASE_URL en env → usarla
3. Si no → "postgresql://techstock:techstock@localhost:5433/techstock"
4. Si empieza con "postgresql" → pool_size=10, max_overflow=20, client_encoding=utf8
5. Si empieza con "sqlite" → check_same_thread=False, StaticPool si in-memory
```

### Frozen mode
Cuando se ejecuta desde PyInstaller (`sys.frozen=True`), `_base_dir` apunta a `os.path.dirname(sys.executable)` para encontrar `.env`, templates y static.

---

## 17. Backup System (routers/backup.py)

### Tablas incluidas en backup
categorias, productos, proveedores, clientes, ventas, detalle_venta, movimientos_inventario, cajas, movimientos_caja, deudas, pagos_deuda, facturas, cobros_factura, acreedores, gastos, configuracion, usuarios

### Formato
Backup SQL (INSERT statements) generado por query directa. Restore ejecuta los INSERTs.

---

## 18. Roadmap

### Completado
- POS: Precio manual editable en carrito
- Ganancias visibles en POS, historial y dashboard
- Filtro temporal en dashboard (fecha_desde/fecha_hasta)
- Busqueda por referencia en POS y listado
- Modulo de Gastos completo (CRUD + 12 tests)
- Instalador Windows .exe (PyInstaller + Inno Setup)
- PostgreSQL portable integrado
- Assets 100% offline (sin CDN)

### Pendiente
1. **Rate limiting** — En endpoints publicos (login)
2. **Image resizing** — Para avatars de perfil
3. **Notificaciones** — Stock bajo, deudas vencidas
4. **Multi-idioma** — Soporte i18n
