# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TechStock v3.0.
Bundles the FastAPI app + launcher into a distributable directory.
Entry point: launcher.py (tkinter GUI that manages PG + uvicorn).
In frozen mode, uvicorn runs in-process (no subprocess Python needed).
"""
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
BASE = os.path.abspath(".")

# ── Hidden imports ────────────────────────────────────────────────
# Everything the app imports at runtime must be listed here because
# PyInstaller can't trace dynamic imports or deferred local imports.
hidden = [
    # App core
    "main", "database", "models", "auth", "middleware",
    "templates_config", "seed", "migrations",
    # Routers (imported dynamically in main.py)
    "routers", "routers.auth_router", "routers.usuarios",
    "routers.productos", "routers.categorias", "routers.proveedores",
    "routers.inventario", "routers.reportes", "routers.deudas",
    "routers.facturas", "routers.acreedores", "routers.gastos",
    "routers.configuracion", "routers.clientes", "routers.ventas",
    "routers.caja", "routers.backup", "routers.importar",
    "routers.perfil", "routers.auditoria",
    "routers.locales", "routers.super_dashboard",
    # Utils
    "utils", "utils.constants", "utils.financial", "utils.pagination",
    "utils.excel", "utils.queries", "utils.dashboard", "utils.pdf",
    # Database drivers (PostgreSQL is the production DB)
    "psycopg2", "psycopg2._psycopg", "psycopg2.extensions",
    "psycopg2.extras", "psycopg2.tz",
    # SQLAlchemy dialects
    "sqlalchemy.dialects.postgresql",
    "sqlalchemy.dialects.postgresql.psycopg2",
    "sqlalchemy.dialects.sqlite",
    # Jinja2
    "jinja2", "jinja2.ext",
    # Multipart (form parsing)
    "multipart", "multipart.multipart",
    # Auth / crypto
    "bcrypt", "bcrypt._bcrypt", "itsdangerous",
    # Excel
    "openpyxl",
    # Async files
    "aiofiles", "aiofiles.os",
    # PDF generation
    "reportlab", "reportlab.lib", "reportlab.lib.pagesizes",
    "reportlab.lib.colors", "reportlab.lib.units", "reportlab.lib.enums",
    "reportlab.lib.styles", "reportlab.platypus",
    "reportlab.pdfbase", "reportlab.pdfbase.pdfmetrics",
    "reportlab.pdfbase._fontdata",
    # Email (used by some stdlib imports)
    "email.mime.text",
    # Encodings (needed for PG and HTTP)
    "encodings", "encodings.utf_8", "encodings.latin_1",
    "encodings.cp1252", "encodings.ascii", "encodings.idna",
]

# Collect ALL submodules for frameworks that do heavy dynamic imports
hidden += collect_submodules("uvicorn")
hidden += collect_submodules("starlette")
hidden += collect_submodules("fastapi")
hidden += collect_submodules("reportlab")

# ── Data files ────────────────────────────────────────────────────
datas = [
    (os.path.join(BASE, "templates"), "templates"),
    (os.path.join(BASE, "static", "css"), os.path.join("static", "css")),
    (os.path.join(BASE, "static", "js"), os.path.join("static", "js")),
    (os.path.join(BASE, "static", "vendor"), os.path.join("static", "vendor")),
    (os.path.join(BASE, "static", "uploads"), os.path.join("static", "uploads")),
]

# Collect psycopg2 data files (bundled DLLs: libpq, libssl, etc.)
datas += collect_data_files("psycopg2")

# PostgreSQL portable is copied by build_installer.bat (too large for datas)

# ── Analysis ──────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(BASE, "launcher.py")],
    pathex=[BASE],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev/test tools (never needed in production)
        "pytest", "httpx", "coverage", "pip", "setuptools", "wheel",
        "pkg_resources", "_pytest",
        # Test frameworks
        "tkinter.test", "unittest", "doctest", "pydoc",
        # Scientific computing (not used)
        "matplotlib", "numpy", "pandas", "scipy",
        # Notebook/IDE tools
        "IPython", "jupyter", "notebook",
        # Network protocols not used
        "ftplib", "imaplib", "poplib", "nntplib", "telnetlib",
        # CGI (not used, we use ASGI)
        "cgi", "cgitb",
        # Unused stdlib
        "curses", "lib2to3", "pdb", "profile", "pstats",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TechStock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # windowed app (tkinter launcher)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BASE, "static", "favicon.ico") if os.path.exists(os.path.join(BASE, "static", "favicon.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TechStock",
)
