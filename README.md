# TechStock v2.0

**Sistema de Inventario y Punto de Venta** para negocios de tecnologia y retail.

Aplicacion web completa con gestion de productos, ventas (POS), caja registradora, cuentas por pagar/cobrar, gastos, reportes, backups y mas. Funciona 100% offline, incluye instalador Windows con PostgreSQL portable.

---

## Caracteristicas Principales

### Gestion de Inventario
- Productos con codigo, referencia, precio costo/venta/minimo, stock, unidad de medida
- Categorias con soft delete y proteccion de cascada
- Proveedores con detalle de deudas asociadas
- Movimientos: entradas, salidas, ajustes con trazabilidad completa
- Alertas de stock bajo automaticas en dashboard

### Punto de Venta (POS)
- Interfaz rapida con busqueda por codigo, nombre o referencia
- Precio manual editable en carrito con precio minimo configurable
- Metodos de pago: efectivo, tarjeta, transferencia, credito
- Calculo automatico de cambio y ganancia visible por venta
- Recibo imprimible

### Caja Registradora
- Apertura/cierre con monto inicial
- Movimientos de ingreso/egreso vinculados a ventas
- Diferencia cierre esperado vs real
- Historial completo de cajas

### Finanzas
- **Cuentas por pagar (Deudas)**: Registro, pagos parciales, vencimientos, reporte
- **Cuentas por cobrar (Facturas)**: Emision, cobros parciales, importacion Excel, reporte
- **Gastos**: Directos/indirectos, 12 categorias predefinidas, filtros avanzados
- **Acreedores**: Gestion de proveedores, bancos, personas

### Dashboard Ejecutivo
- 7 graficas interactivas (Chart.js)
- Filtro temporal configurable (fecha desde/hasta)
- Metricas: ventas, ganancias, inventario, stock bajo, deudas, facturas
- Top 5 productos mas vendidos

### Seguridad
- Autenticacion con cookies firmadas (bcrypt + itsdangerous)
- 3 roles: Admin, Vendedor, Bodeguero
- Permisos granulares por usuario (14 modulos)
- Proteccion CSRF en todos los formularios
- Audit trail completo (quien, que, cuando, desde donde)
- Multi-cuenta: cambiar entre usuarios sin cerrar sesion

### Reportes y Exportacion
- Reportes de stock y movimientos con filtros
- Exportacion Excel (productos, reportes, facturas)
- Importacion Excel (categorias, productos, facturas)
- Recibos de venta en formato imprimible

### Backup y Restauracion
- Backup completo de la base de datos (17 tablas)
- Restauracion desde archivo SQL
- Interfaz web para gestion de backups

---

## Stack Tecnologico

| Capa | Tecnologia | Version |
|------|------------|---------|
| Backend | FastAPI + SQLAlchemy 2.0 | 0.115 / 2.0.35 |
| Base de datos | PostgreSQL (portable incluido) | 16 |
| Frontend | Jinja2 + Bootstrap 5.3 + Vanilla JS | SSR |
| Auth | Cookies firmadas + bcrypt + RBAC | itsdangerous 2.2 |
| Reportes | openpyxl (Excel) + ReportLab (PDF) | 3.1.5 / 4.2+ |
| Server | Uvicorn (ASGI) | 0.30.6 |
| Tests | pytest + httpx (258 tests) | 8.0+ |
| CI/CD | GitHub Actions | Python 3.10/3.11/3.12 |
| Build | PyInstaller + Inno Setup 6 | Instalador .exe |
| Docker | docker-compose + postgres:16-alpine | Compose 3.9 |

**Principio clave**: 100% offline. Todos los assets (Bootstrap, Icons, Chart.js) son locales. Sin CDN.

---

## Requisitos

### Para desarrollo
- Python 3.10+ (recomendado 3.11)
- PostgreSQL 16 (o usar Docker Compose)
- Git

### Para usuarios finales (instalador Windows)
- Windows 10/11 (64-bit)
- 500 MB espacio en disco
- No requiere software adicional (todo incluido en el instalador)
- Funciona en redes protegidas (no necesita internet)

---

## Instalacion para Desarrollo

### 1. Clonar repositorio
```bash
git clone <repo-url>
cd inventario-tech
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
# Produccion:
pip install -r requirements.txt

# Desarrollo (incluye pytest, httpx, coverage):
pip install -r requirements-dev.txt
```

### 4. Configurar base de datos

**Opcion A: PostgreSQL local**
```bash
# Crear base de datos y usuario
psql -U postgres -c "CREATE USER techstock WITH PASSWORD 'techstock' CREATEDB;"
psql -U postgres -c "CREATE DATABASE techstock OWNER techstock;"

# Configurar .env
cp .env.example .env
# Editar DATABASE_URL si cambia de los defaults
```

**Opcion B: Docker Compose (solo PostgreSQL)**
```bash
docker-compose up -d db
# PostgreSQL disponible en localhost:5432
# Configurar .env: DATABASE_URL=postgresql://techstock:techstock_pass@localhost:5432/techstock
```

### 5. Ejecutar
```bash
python main.py
```

Al iniciar, el sistema muestra:
```
TechStock v2.0 - Sistema de Inventario
  Acceso local:    http://localhost:8000
  Acceso en red:   http://192.168.x.x:8000
```

**Login por defecto**: admin / admin123

---

## Tests

```bash
# Suite completa (258 tests, con cobertura)
pytest

# Modulo especifico
pytest tests/test_ventas.py -v

# Resumen rapido
pytest --tb=short -q

# Test especifico por nombre
pytest -k "test_crear_venta"

# Cobertura HTML detallada
pytest --cov --cov-report=html
# Abrir htmlcov/index.html
```

Los tests usan **SQLite in-memory** (no requieren PostgreSQL). Configuracion en `pytest.ini`.

### CI/CD
GitHub Actions ejecuta tests automaticamente en Python 3.10, 3.11 y 3.12 en cada push/PR a `main`. Ver `.github/workflows/ci.yml`.

---

## Deploy

### Opcion 1: Docker Compose (servidores Linux/Mac)
```bash
docker-compose up -d
# App: http://localhost:8000
# PostgreSQL: localhost:5432 (interno, no requiere acceso directo)
```

### Opcion 2: Instalador Windows (usuarios finales)
```bash
# Desde la raiz del proyecto (requiere PyInstaller + Inno Setup 6 instalados)
build_installer.bat
# Output: dist/installer/TechStock_Setup_v2.0.exe (~48 MB)
```

El instalador incluye:
- Aplicacion TechStock empaquetada con PyInstaller
- PostgreSQL 16 portable (puerto 5433, datos en %APPDATA%/TechStock)
- Launcher GUI dark-theme con gestion de PostgreSQL + servidor
- Modos: **Instalar** / **Reparar** / **Desinstalar**

### Opcion 3: Desarrollo directo
```bash
pip install -r requirements.txt
# Tener PostgreSQL corriendo (ver Opcion A arriba)
python main.py
```

---

## Arquitectura Multi-Equipo

```
Red Local (LAN/WiFi)
│
├── PC Servidor ──► TechStock.exe (launcher + PG + web)
│   └── %APPDATA%/TechStock/pgdata (PostgreSQL)
│
├── PC Vendedor 1 ──► http://192.168.x.x:8000 (navegador)
├── PC Vendedor 2 ──► http://192.168.x.x:8000 (navegador)
├── Tablet Caja   ──► http://192.168.x.x:8000 (navegador)
└── Celular Admin ──► http://192.168.x.x:8000 (navegador)
```

Solo un equipo ejecuta TechStock. Los demas acceden por navegador web. Funciona en redes protegidas sin internet.

---

## Estructura del Proyecto

```
inventario-tech/
├── main.py              # App FastAPI + dashboard + startup
├── database.py          # Conexion DB (PostgreSQL/SQLite auto)
├── models.py            # 17 modelos SQLAlchemy
├── auth.py              # Auth + RBAC + CSRF + audit trail
├── middleware.py         # Auth middleware + CSRF validation
├── templates_config.py  # Jinja2 + filtros + globals
├── seed.py              # Datos iniciales (admin + config)
├── migrations.py        # Migraciones idempotentes (sin Alembic)
├── launcher.py          # GUI tkinter para servidor + PostgreSQL
│
├── routers/             # 19 routers, 128+ endpoints
├── templates/           # 47 HTML (Jinja2, herencia base.html)
├── static/              # CSS, JS, vendor/ (Bootstrap, Icons, Chart.js)
├── tests/               # 258 tests (pytest + httpx)
├── utils/               # Constantes, paginacion, Excel, financiero
├── installer/           # Inno Setup script (.iss)
├── .claude/commands/    # 7 skills para Claude Code AI
├── .github/workflows/   # CI: GitHub Actions
│
├── techstock.spec       # PyInstaller spec
├── build_installer.bat  # Automatizacion build
├── Dockerfile           # Docker image
├── docker-compose.yml   # PostgreSQL + app
├── requirements.txt     # Dependencias produccion (11)
├── requirements-dev.txt # + pytest, httpx, coverage
└── pytest.ini           # Config testing
```

---

## Modulos del Sistema

| Modulo | Router | Endpoints | Descripcion |
|--------|--------|-----------|-------------|
| Auth | auth_router.py | 5 | Login, logout, multi-cuenta |
| Usuarios | usuarios.py | 6 | CRUD + roles + permisos granulares |
| Productos | productos.py | 6 | CRUD + busqueda + Excel export |
| Categorias | categorias.py | 4 | CRUD + cascade protection |
| Proveedores | proveedores.py | 7 | CRUD + detalle con deudas |
| Clientes | clientes.py | 7 | CRUD + detalle con ventas |
| Inventario | inventario.py | 6 | Entradas, salidas, ajustes, historial |
| Ventas/POS | ventas.py | 8 | POS, historial, detalle, recibo, anulacion |
| Caja | caja.py | 8 | Apertura, cierre, movimientos, historial |
| Deudas | deudas.py | 11 | CRUD + pagos parciales + reporte |
| Facturas | facturas.py | 11 | CRUD + cobros + import Excel + reporte |
| Acreedores | acreedores.py | 6 | CRUD acreedores |
| Gastos | gastos.py | 7 | CRUD + categorias + filtros avanzados |
| Reportes | reportes.py | 7 | Stock, movimientos, Excel exports |
| Configuracion | configuracion.py | 3 | Nombre negocio, moneda, recibo |
| Importar | importar.py | 3 | Excel: categorias, productos, facturas |
| Backup | backup.py | 7 | Backup/restore DB completo |
| Perfil | perfil.py | 5 | Editar perfil + avatar |
| Auditoria | auditoria.py | 1 | Log de acciones del sistema |

---

## Modelos de Datos (17 modelos)

```
Usuario ──1:N──> AuditLog
Usuario ──1:N──> Venta (vendedor)
Usuario ──1:N──> Caja

Categoria ──1:N──> Producto ──1:N──> MovimientoInventario
Proveedor ──1:N──> Producto          ──1:N──> DetalleVenta
Proveedor ──1:N──> MovimientoInventario
Proveedor ──1:N──> Deuda

Cliente ──1:N──> Venta ──1:N──> DetalleVenta
Venta ──N:1──> Caja ──1:N──> MovimientoCaja

Acreedor ──1:N──> Deuda ──1:N──> PagoDeuda
Factura ──1:N──> PagoFactura

Gasto (standalone)
Configuracion (singleton)
```

---

## Configuracion

### Variables de entorno (.env)
```bash
# PostgreSQL (default: portable en puerto 5433)
DATABASE_URL=postgresql://techstock:techstock@localhost:5433/techstock

# Admin inicial (solo primer inicio, opcional)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_NAME=Administrador
```

### Configuracion del negocio (via interfaz web)
Accesible desde el menu **Configuracion** (solo Admin):
- Nombre del negocio, NIT/RUC
- Direccion, telefono, email
- Simbolo y codigo de moneda (default: $ COP)
- Mensaje del recibo y pie de factura

---

## Roles y Permisos

| Rol | Acceso | Modulos |
|-----|--------|---------|
| **ADMIN** | Total | Todos (14 modulos) |
| **VENDEDOR** | Operativo | Dashboard, Productos, POS, Historial, Clientes, Caja, Acreedores, Deudas, Facturas, Gastos, Reportes |
| **BODEGUERO** | Inventario | Dashboard, Productos, Categorias, Inventario, Proveedores, Reportes |

Cada usuario puede tener **permisos personalizados** que sobreescriben los del rol.

---

## Guia para Desarrolladores

### Agregar un nuevo modulo

1. **Modelo** (`models.py`): Clase SQLAlchemy con `activo = Column(Boolean, default=True)`
2. **Migracion** (`migrations.py`): Funcion idempotente para ALTER TABLE
3. **Router** (`routers/<modulo>.py`): CRUD con `require_permiso`, `log_audit`, CSRF
4. **Templates** (`templates/<modulo>/`): Extender `base.html`
5. **Sidebar** (`templates/base.html`): Enlace con icono Bootstrap Icons
6. **Permisos** (`auth.py`): Agregar a `MODULOS_DISPONIBLES` y `PERMISOS_POR_ROL`
7. **Registro** (`main.py`): `app.include_router(modulo.router)`
8. **Tests** (`tests/test_<modulo>.py`): Fixtures en `conftest.py`
9. **Constantes** (`utils/constants.py`): Listas fijas centralizadas

### Reglas criticas
- **POST → redirect 303** (patron PRG, siempre)
- **Nunca `db.delete()`** — soft delete con `activo=False` o `estado="ANULADO"`
- **CSRF en todo form POST** — `{{ csrf_token(request) }}`
- **Audit en toda mutacion** — `log_audit(db, user, accion, entidad, id, detalle, ip)`
- **Assets locales** — nunca CDN, todo en `static/vendor/`
- **Errores al usuario** — redirect con `?error=`, nunca HTTP 500

### Convencion de commits
```
feat:     Nueva funcionalidad
fix:      Correccion de bug
docs:     Documentacion
refactor: Refactorizacion
chore:    Mantenimiento
```

---

## Trabajo con IA (Claude Code)

Este proyecto esta preparado para desarrollo asistido por IA:

- **CLAUDE.md**: Guia completa para orientacion automatica de agentes IA
- **Skills** (`.claude/commands/`): 7 comandos slash para flujos estructurados
  - `/test` — Ejecutar tests
  - `/feature` — Implementar feature completa
  - `/fix` — Diagnosticar y corregir bug (TDD)
  - `/status` — Reporte del proyecto
  - `/build` — Construir instalador
  - `/review-code` — Review de calidad/seguridad
  - `/deploy` — Checklist pre-deploy

Los agentes IA pueden usar agentes especializados:
- **Explore agent**: Para investigar codigo y relaciones
- **Plan agent**: Para disenar implementaciones
- **General-purpose agent**: Para tareas paralelas (tests, builds)

---

## Creditos

- **Desarrollador**: Sebastian Pava — [Orionics](https://orionics.com)
- **Ubicacion**: Barrancabermeja, Colombia
- **Stack**: FastAPI + SQLAlchemy + PostgreSQL + Bootstrap 5

---

*TechStock v2.0 — Sistema de Inventario y Punto de Venta*
*Orionics 2026*
