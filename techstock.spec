# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TechStock v2.0.
Bundles the FastAPI app + launcher into a distributable directory.
"""
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
BASE = os.path.abspath(".")

# ── Hidden imports ────────────────────────────────────────────────
# FastAPI/Starlette internals + all app modules
hidden = [
    # App modules
    "main", "database", "models", "auth", "middleware",
    "templates_config", "seed", "migrations",
    # Routers
    "routers", "routers.auth_router", "routers.usuarios",
    "routers.productos", "routers.categorias", "routers.proveedores",
    "routers.inventario", "routers.reportes", "routers.deudas",
    "routers.facturas", "routers.acreedores", "routers.gastos",
    "routers.configuracion", "routers.clientes", "routers.ventas",
    "routers.caja", "routers.backup", "routers.importar",
    "routers.perfil", "routers.auditoria",
    # Utils
    "utils", "utils.excel", "utils.search",
    "utils.financial", "utils.pagination",
    # Dependencies
    "uvicorn", "uvicorn.logging", "uvicorn.loops",
    "uvicorn.loops.auto", "uvicorn.protocols",
    "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "fastapi", "starlette", "starlette.routing",
    "starlette.middleware", "starlette.responses",
    "sqlalchemy", "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.postgresql",
    "jinja2", "jinja2.ext",
    "multipart", "multipart.multipart",
    "bcrypt", "itsdangerous",
    "openpyxl", "aiofiles",
    "reportlab", "reportlab.lib", "reportlab.platypus",
    "email.mime.text",
    "encodings", "encodings.utf_8", "encodings.latin_1",
    "encodings.cp1252", "encodings.ascii",
]

# Collect all uvicorn/starlette submodules (they do dynamic imports)
hidden += collect_submodules("uvicorn")
hidden += collect_submodules("starlette")
hidden += collect_submodules("fastapi")

# ── Data files ────────────────────────────────────────────────────
datas = [
    (os.path.join(BASE, "templates"), "templates"),
    (os.path.join(BASE, "static", "css"), os.path.join("static", "css")),
    (os.path.join(BASE, "static", "js"), os.path.join("static", "js")),
    (os.path.join(BASE, "static", "vendor"), os.path.join("static", "vendor")),
    (os.path.join(BASE, "static", "uploads"), os.path.join("static", "uploads")),
]

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
        # Not needed for standalone SQLite mode
        "psycopg2", "psycopg2._psycopg",
        # Dev/test tools
        "pytest", "httpx", "coverage", "pip", "setuptools",
        # Unnecessary for production
        "tkinter.test", "unittest", "doctest",
        "matplotlib", "numpy", "pandas", "scipy",
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
