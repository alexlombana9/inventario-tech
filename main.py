import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date
import uvicorn
import socket

from starlette.exceptions import HTTPException as StarletteHTTPException

# ── Logging estructurado ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("techstock")

from sqlalchemy.exc import OperationalError

from database import engine, Base, get_db
from database import SessionLocal
from templates_config import templates
from middleware import AuthMiddleware
from auth import get_flash, user_has_permiso, get_local_id
import models


# ── Lifespan: startup y shutdown ─────────────────────────────
@asynccontextmanager
async def lifespan(app_instance):  # pragma: no cover
    """Ciclo de vida de la aplicacion: startup y shutdown."""
    # ── Startup ──
    logger.info("TechStock v4.0 iniciando...")

    if os.environ.get("TESTING") != "1":
        # Health check: verificar conexion antes de crear tablas
        _startup_ok = False
        for _attempt in range(3):
            try:
                with engine.connect() as _conn:
                    _conn.execute(text("SELECT 1"))
                _startup_ok = True
                break
            except Exception as _e:
                logger.warning(f"DB connection attempt {_attempt + 1}/3 failed: {_e}")
                import time; time.sleep(2)
        if not _startup_ok:
            logger.error("No se pudo conectar a PostgreSQL despues de 3 intentos.")

        try:
            Base.metadata.create_all(bind=engine)

            from migrations import run_migrations
            run_migrations(engine)

            from seed import run_seed
            _seed_db = SessionLocal()
            try:
                run_seed(_seed_db)
            finally:
                _seed_db.close()
        except Exception as _startup_err:
            logger.error(f"Error durante inicializacion de DB: {_startup_err}")

    logger.info("TechStock v4.0 listo.")
    yield

    # ── Shutdown ──
    if os.environ.get("TESTING") != "1":
        logger.info("TechStock cerrando conexiones...")
        engine.dispose()
        logger.info("TechStock detenido correctamente.")


# ── App ──
app = FastAPI(title="TechStock v4.0 - Sistema de Inventario", lifespan=lifespan)
app.add_middleware(AuthMiddleware)
_static_dir = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__)),
    "static"
)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/sw.js")
async def service_worker():
    """Service worker servido desde raiz para scope completo."""
    return FileResponse(
        os.path.join(_static_dir, "sw.js"),
        media_type="application/javascript",
    )


# ── Exception Handlers ──
@app.exception_handler(OperationalError)
async def db_connection_error_handler(request: Request, exc: OperationalError):
    """Muestra error amigable cuando PostgreSQL no responde."""
    logger.error(f"DB connection error: {exc}")
    return RedirectResponse(
        "/login?error=Error+de+conexion+a+la+base+de+datos.+Verifica+que+PostgreSQL+este+activo.",
        status_code=303,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Paginas de error personalizadas para 404 y 500."""
    if exc.status_code == 404:
        return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)
    if exc.status_code == 500:
        return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)
    # Para otros codigos, respuesta JSON simple
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Captura errores no manejados y muestra pagina 500."""
    logger.exception(f"Error no manejado en {request.method} {request.url.path}")
    return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)


# ── Health Endpoints ──
@app.get("/health")
async def health_check():
    """Liveness probe — confirma que el proceso esta vivo."""
    return {"status": "ok", "version": "4.0.0"}


@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe — verifica conexion a base de datos."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "disconnected"})

# ── Routers ──
from routers import productos, categorias, proveedores, inventario, reportes, deudas, facturas, acreedores, gastos
from routers import auth_router, usuarios, configuracion, clientes, ventas, caja, backup, importar, perfil, auditoria
from routers import locales as locales_router
from routers import super_dashboard as super_dashboard_router
from routers import chatbot as chatbot_router

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
app.include_router(chatbot_router.router)


def _base_context(request: Request) -> dict:
    """Contexto base que incluye usuario actual, local y flash messages.

    Reutiliza datos ya cargados por el middleware (request.state) para evitar
    abrir sesiones de DB extra en cada request. Los indicadores de movimientos
    del topbar se obtienen via el Jinja2 global movimientos_hoy(request).
    """
    flash = get_flash(request)
    user = getattr(request.state, "user", None)
    local_id = getattr(request.state, "local_id", None)
    selected_local_id = getattr(request.state, "selected_local_id", None)

    # Reutilizar datos ya cargados por el middleware en vez de queries extra
    current_local_name = getattr(request.state, "local_name", None)
    all_locales = getattr(request.state, "all_locales", [])

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
    ctx.update(get_general_metrics(db, fd_dt, fh_dt, local_id=lid))
    ctx.update(get_period_metrics(db, fd_dt, fh_dt, local_id=lid))
    ctx.update(get_financial_metrics(db, fd_dt, fh_dt, local_id=lid))
    ctx.update(get_tables_data(db, fd_dt, fh_dt, local_id=lid))
    ctx.update(get_chart_data(db, fd_dt, fh_dt, fh, local_id=lid))
    ctx["fecha_hoy"] = hoy.strftime("%d de %B de %Y")
    ctx["periodo_label"] = f"{fd.strftime('%d/%m/%Y')} — {fh.strftime('%d/%m/%Y')}"

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
    logger.info("  TechStock v4.0 - Sistema de Inventario")
    logger.info("=" * 55)
    logger.info("  Acceso local:    http://localhost:8000")
    logger.info("  Acceso en red:   http://%s:8000", ip)
    logger.info("  Presiona CTRL+C para detener el servidor")
    logger.info("=" * 55)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
