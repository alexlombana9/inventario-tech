import os
import io
import subprocess
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, DATABASE_URL
from templates_config import templates
from auth import require_role, log_audit
import models

router = APIRouter(prefix="/backup", tags=["backup"])

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")


def _parse_pg_url(url: str) -> dict:
    """Extrae host, port, dbname, user, password de la DATABASE_URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": (parsed.path or "/inventario").lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def _pg_dump_sql(pg: dict) -> bytes | None:
    """Intenta ejecutar pg_dump y retorna los bytes del dump, o None si falla."""
    env = os.environ.copy()
    if pg["password"]:
        env["PGPASSWORD"] = pg["password"]
    try:
        result = subprocess.run(
            [
                "pg_dump",
                "-h", pg["host"],
                "-p", pg["port"],
                "-U", pg["user"],
                "-d", pg["dbname"],
                "--no-owner",
                "--no-acl",
            ],
            capture_output=True,
            env=env,
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _fallback_dump(db: Session) -> bytes:
    """Genera un dump SQL básico usando SQLAlchemy cuando pg_dump no está disponible."""
    lines = [
        f"-- TechStock Backup (fallback)",
        f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"-- Nota: Este es un respaldo parcial generado sin pg_dump.",
        f"--       Para respaldos completos, instale postgresql-client.\n",
    ]

    tables = [
        "usuarios", "categorias", "proveedores", "productos",
        "movimientos_inventario", "clientes", "ventas", "detalle_venta",
        "cajas", "movimientos_caja", "deudas", "pagos_deuda",
        "facturas", "cobros_factura", "configuracion", "audit_log",
    ]

    for table_name in tables:
        try:
            rows = db.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            if not rows:
                continue
            columns = db.execute(text(
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
            )).fetchall()
            col_names = [c[0] for c in columns]

            lines.append(f"\n-- Tabla: {table_name} ({len(rows)} registros)")
            for row in rows:
                vals = []
                for v in row:
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, str):
                        vals.append("'" + v.replace("'", "''") + "'")
                    elif isinstance(v, datetime):
                        vals.append(f"'{v.isoformat()}'")
                    elif isinstance(v, bool):
                        vals.append("TRUE" if v else "FALSE")
                    else:
                        vals.append(str(v))
                cols_str = ", ".join(col_names)
                vals_str = ", ".join(vals)
                lines.append(f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str});")
        except Exception:
            lines.append(f"-- Error exportando tabla: {table_name}")

    return "\n".join(lines).encode("utf-8")


@router.get("")
def backup_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    msg: str = None,
    error: str = None,
):
    backups = []
    if os.path.exists(BACKUP_DIR):
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith(".sql"):
                path = os.path.join(BACKUP_DIR, f)
                size = os.path.getsize(path)
                backups.append({
                    "filename": f,
                    "size": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "date": datetime.fromtimestamp(os.path.getmtime(path)),
                })

    return templates.TemplateResponse("backup/index.html", {
        "request": request,
        "backups": backups,
        "msg": msg,
        "error": error,
    })


@router.get("/descargar")
def descargar_backup(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    pg = _parse_pg_url(DATABASE_URL)
    content = _pg_dump_sql(pg)

    if content is None:
        content = _fallback_dump(db)

    buffer = io.BytesIO(content)
    buffer.seek(0)

    filename = f"techstock_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "backup", None, f"Backup descargado: {filename}", ip)

    return StreamingResponse(
        buffer,
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/crear")
def crear_backup_local(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    os.makedirs(BACKUP_DIR, exist_ok=True)

    filename = f"techstock_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    dest_path = os.path.join(BACKUP_DIR, filename)

    pg = _parse_pg_url(DATABASE_URL)
    content = _pg_dump_sql(pg)

    if content is None:
        content = _fallback_dump(db)

    with open(dest_path, "wb") as f:
        f.write(content)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "backup", None, f"Backup local creado: {filename}", ip)

    return RedirectResponse(f"/backup?msg=Backup+creado:+{filename}", status_code=303)
