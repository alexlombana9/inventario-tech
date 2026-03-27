import os
import sys
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import uvicorn
import socket

# ── Logging estructurado ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("techstock")

from database import engine, Base, get_db
from templates_config import templates
from middleware import AuthMiddleware
from auth import get_flash, user_has_permiso, get_local_id
import models

# ── Crear tablas y ejecutar migraciones (solo en producción) ──
if os.environ.get("TESTING") != "1":  # pragma: no cover
    Base.metadata.create_all(bind=engine)

    from migrations import run_migrations
    run_migrations(engine)

    from seed import run_seed
    from database import SessionLocal
    _seed_db = SessionLocal()
    try:
        run_seed(_seed_db)
    finally:
        _seed_db.close()

# ── App ──
app = FastAPI(title="TechStock - Sistema de Inventario")
app.add_middleware(AuthMiddleware)
_static_dir = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__)),
    "static"
)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# ── Routers ──
from routers import productos, categorias, proveedores, inventario, reportes, deudas, facturas, acreedores, gastos
from routers import auth_router, usuarios, configuracion, clientes, ventas, caja, backup, importar, perfil, auditoria
from routers import locales as locales_router
from routers import super_dashboard as super_dashboard_router

app.include_router(auth_router.router)
app.include_router(usuarios.router)
app.include_router(configuracion.router)
app.include_router(clientes.router)
app.include_router(ventas.router)
app.include_router(caja.router)
app.include_router(backup.router)
app.include_router(importar.router)
app.include_router(perfil.router)
app.include_router(auditoria.router)
app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(proveedores.router)
app.include_router(inventario.router)
app.include_router(reportes.router)
app.include_router(deudas.router)
app.include_router(facturas.router)
app.include_router(acreedores.router)
app.include_router(gastos.router)
app.include_router(locales_router.router)
app.include_router(super_dashboard_router.router)


def _base_context(request: Request) -> dict:
    """Contexto base que incluye usuario actual, local y flash messages."""
    flash = get_flash(request)
    user = getattr(request.state, "user", None)
    local_id = getattr(request.state, "local_id", None)
    selected_local_id = getattr(request.state, "selected_local_id", None)

    # Cargar nombre del local seleccionado para SUPERADMIN
    current_local_name = None
    all_locales = []
    if user and user.rol == "SUPERADMIN":
        from database import SessionLocal
        _db = SessionLocal()
        try:
            all_locales = _db.query(models.Local).filter(models.Local.activo == True).all()
            if selected_local_id:
                local_obj = _db.query(models.Local).filter(models.Local.id == selected_local_id).first()
                if local_obj:
                    current_local_name = local_obj.nombre
        finally:
            _db.close()
    elif user and user.local_id:
        from database import SessionLocal
        _db = SessionLocal()
        try:
            local_obj = _db.query(models.Local).filter(models.Local.id == user.local_id).first()
            if local_obj:
                current_local_name = local_obj.nombre
        finally:
            _db.close()

    return {
        "request": request,
        "current_user": user,
        "flash": flash,
        "local_id": local_id,
        "selected_local_id": selected_local_id,
        "current_local_name": current_local_name,
        "all_locales": all_locales,
    }


@app.get("/guia")
def guia(request: Request):
    ctx = _base_context(request)
    return templates.TemplateResponse("guia/index.html", ctx)


@app.get("/legal")
def legal(request: Request):
    ctx = _base_context(request)
    return templates.TemplateResponse("legal/index.html", ctx)


@app.get("/")
def index(
    request: Request,
    db: Session = Depends(get_db),
    fecha_desde: str = None,
    fecha_hasta: str = None,
):
    user = getattr(request.state, "user", None)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # SUPERADMIN sin local seleccionado va al super dashboard
    if user.rol == "SUPERADMIN" and not getattr(request.state, "selected_local_id", None):
        return RedirectResponse("/super", status_code=303)

    from utils.dashboard import (
        get_date_range, get_general_metrics, get_period_metrics,
        get_financial_metrics, get_tables_data, get_chart_data,
    )

    hoy = date.today()
    ctx = _base_context(request)
    lid = getattr(request.state, "local_id", None)

    fd, fh, fd_dt, fh_dt = get_date_range(fecha_desde, fecha_hasta, hoy)

    ctx.update({"fecha_desde": fd.strftime("%Y-%m-%d"), "fecha_hasta": fh.strftime("%Y-%m-%d")})
    ctx.update(get_general_metrics(db, local_id=lid))
    ctx.update(get_period_metrics(db, fd_dt, fh_dt, local_id=lid))
    ctx.update(get_financial_metrics(db, local_id=lid))
    ctx.update(get_tables_data(db, local_id=lid))
    ctx.update(get_chart_data(db, fd_dt, fh_dt, fh, local_id=lid))
    ctx["fecha_hoy"] = hoy.strftime("%d de %B de %Y")

    return templates.TemplateResponse("index.html", ctx)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = get_local_ip()
    logger.info("=" * 55)
    logger.info("  TechStock v3.0 - Sistema de Inventario")
    logger.info("=" * 55)
    logger.info("  Acceso local:    http://localhost:8000")
    logger.info("  Acceso en red:   http://%s:8000", ip)
    logger.info("  Presiona CTRL+C para detener el servidor")
    logger.info("=" * 55)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
