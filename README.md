# TechStock — Sistema de Inventario para Locales Tecnológicos

Sistema de inventario local para tiendas y locales comerciales de tecnología. Corre completamente en tu red local sin necesidad de internet ni servicios en la nube.

## Características

### Módulos actuales (v1.0)
- **Dashboard** — Resumen en tiempo real: valor del inventario, stock bajo, movimientos del día
- **Productos** — CRUD completo con código, precios de costo/venta, stock mínimo y cálculo de margen
- **Categorías** — Organización de productos con sugerencias preconfiguradas para tiendas tech
- **Proveedores** — Registro de proveedores con historial de entradas por proveedor
- **Inventario** — Registro de entradas, salidas y ajustes de stock con historial paginado
- **Reportes** — Reporte de stock actual y movimientos por período, ambos exportables a **PDF**

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.10+ · FastAPI · SQLAlchemy |
| Base de datos | SQLite (WAL mode para multi-usuario) |
| Frontend | Jinja2 · Bootstrap 5 · Bootstrap Icons |
| PDF | ReportLab |
| Servidor | Uvicorn (accesible en red local) |

## Requisitos

- Python 3.10 o superior
- Windows 10/11 (también funciona en Linux/macOS)
- Los demás equipos en red solo necesitan un navegador web

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/techstock.git
cd techstock
```

### 2. Instalar dependencias

**Windows (doble clic):**
```
install.bat
```

**Manual:**
```bash
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 3. Iniciar el sistema

**Windows (doble clic):**
```
start.bat
```

**Manual:**
```bash
python main.py
```

Al iniciar, el sistema muestra las direcciones de acceso:

```
=======================================================
  TechStock - Sistema de Inventario
=======================================================
  Acceso local:    http://localhost:8000
  Acceso en red:   http://192.168.1.10:8000
=======================================================
```

Los demás equipos en la red local acceden usando la **URL en red** desde su navegador.

## Estructura del Proyecto

```
techstock/
├── main.py                  # App FastAPI, rutas raíz
├── database.py              # Configuración SQLAlchemy / SQLite
├── models.py                # Modelos de base de datos
├── templates_config.py      # Instancia Jinja2 compartida + filtros
├── requirements.txt
├── install.bat              # Instalador Windows
├── start.bat                # Iniciador Windows
│
├── routers/
│   ├── productos.py
│   ├── categorias.py
│   ├── proveedores.py
│   ├── inventario.py
│   └── reportes.py          # Incluye exportación PDF
│
├── templates/
│   ├── base.html            # Layout principal (sidebar + topbar)
│   ├── index.html           # Dashboard
│   ├── productos/
│   ├── proveedores/
│   ├── categorias/
│   ├── inventario/
│   └── reportes/
│
└── static/
    ├── css/style.css
    └── js/main.js
```

## Arquitectura Multi-Equipo

```
Red Local (LAN)
│
├── PC Servidor ──► python main.py
│   └── inventario.db (SQLite WAL)
│
├── PC Cliente 1 ──► http://192.168.x.x:8000  (navegador)
├── PC Cliente 2 ──► http://192.168.x.x:8000  (navegador)
└── PC Cliente N ──► http://192.168.x.x:8000  (navegador)
```

> **Nota:** Solo un equipo corre el servidor (`main.py`). Los demás acceden vía browser. La base de datos vive en el equipo servidor.

## Modelos de Datos

```
Categoria       Proveedor
    │               │
    └──► Producto ◄─┘
              │
              └──► MovimientoInventario
                   (ENTRADA / SALIDA / AJUSTE)
```

## Uso Básico

### Flujo recomendado al iniciar
1. Crear **Categorías** (o usar las sugeridas)
2. Registrar **Proveedores**
3. Crear **Productos** con precio costo/venta y stock mínimo
4. Registrar **Entradas** de mercancía al recibir stock
5. Consultar **Reportes** para análisis

### Registrar una entrada de mercancía
1. Ir a **Compras → Registrar Entrada**
2. Seleccionar el producto
3. Ingresar cantidad, precio unitario y número de factura/remisión
4. Opcionalmente seleccionar el proveedor
5. Confirmar → el stock se actualiza automáticamente

### Exportar reporte a PDF
- En **Reportes → Stock Actual** o **Reportes → Movimientos**, hacer clic en el botón **Exportar PDF**
- El PDF se descarga directamente con fecha en el nombre del archivo

## Roadmap

Consulta [`ROADMAP.md`](ROADMAP.md) para ver las funcionalidades planificadas.

## Changelog

Consulta [`CHANGELOG.md`](CHANGELOG.md) para el historial de versiones.

## Contribuir

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nombre-funcionalidad`
3. Realiza tus cambios y haz commit: `git commit -m "feat: descripción"`
4. Abre un Pull Request describiendo los cambios

### Convención de commits

```
feat:     Nueva funcionalidad
fix:      Corrección de bug
docs:     Cambios en documentación
style:    Cambios de formato/estilo
refactor: Refactorización de código
chore:    Tareas de mantenimiento
```

## Licencia

MIT License — libre de usar, modificar y distribuir.
