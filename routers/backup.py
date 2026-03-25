import os
import io
import subprocess
from datetime import datetime
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, DATABASE_URL
from templates_config import templates
from auth import require_role, set_flash, log_audit
import models

router = APIRouter(prefix="/backup", tags=["backup"])

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")
MAX_BACKUP_SIZE = 50 * 1024 * 1024  # 50 MB


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

    # Whitelist de tablas válidas (defensa en profundidad)
    valid_tables = set(tables)

    for table_name in tables:
        if table_name not in valid_tables:
            continue
        try:
            rows = db.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            if not rows:
                continue
            columns = db.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_name = :tname ORDER BY ordinal_position"),
                {"tname": table_name}
            ).fetchall()
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
        except Exception as e:
            lines.append(f"-- Error exportando tabla {table_name}: {type(e).__name__}")

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

    resp = RedirectResponse("/backup", status_code=303)
    return set_flash(resp, f"Backup creado: {filename}")


@router.post("/subir")
async def subir_backup(
    request: Request,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    # Validar extension
    if not archivo.filename or not archivo.filename.endswith(".sql"):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Solo se permiten archivos .sql", "error")

    # Leer y validar tamano
    content = await archivo.read()
    if len(content) > MAX_BACKUP_SIZE:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "El archivo no puede superar 50 MB.", "error")

    if len(content) == 0:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "El archivo esta vacio.", "error")

    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Sanitizar nombre: solo alfanumericos, guiones, puntos y guion bajo
    safe_name = "".join(c for c in archivo.filename if c.isalnum() or c in "-_.")
    if not safe_name.endswith(".sql"):
        safe_name += ".sql"
    # Agregar timestamp para evitar colisiones
    base = safe_name[:-4]
    safe_name = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    dest_path = os.path.join(BACKUP_DIR, safe_name)
    with open(dest_path, "wb") as f:
        f.write(content)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "backup", None,
              f"Backup subido: {safe_name} ({len(content)} bytes)", ip)

    resp = RedirectResponse("/backup", status_code=303)
    return set_flash(resp, f"Backup subido correctamente: {safe_name}")


@router.get("/descargar-local/{filename}")
def descargar_backup_local(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    # Sanitizar: solo permitir nombre de archivo sin path traversal
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".sql"):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Archivo no valido", "error")

    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.isfile(filepath):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Archivo no encontrado", "error")

    with open(filepath, "rb") as f:
        content = f.read()

    buffer = io.BytesIO(content)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"}
    )


@router.post("/restaurar/{filename}")
def restaurar_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".sql"):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Archivo no valido", "error")

    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.isfile(filepath):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Archivo no encontrado", "error")

    pg = _parse_pg_url(DATABASE_URL)

    # Intentar restaurar con psql
    env = os.environ.copy()
    if pg["password"]:
        env["PGPASSWORD"] = pg["password"]

    try:
        result = subprocess.run(
            [
                "psql",
                "-h", pg["host"],
                "-p", pg["port"],
                "-U", pg["user"],
                "-d", pg["dbname"],
                "-f", filepath,
            ],
            capture_output=True,
            env=env,
            timeout=300,
        )
        if result.returncode == 0:
            ip = request.client.host if request.client else ""
            log_audit(db, current_user, "UPDATE", "backup", None,
                      f"Backup restaurado con psql: {safe_name}", ip)
            resp = RedirectResponse("/backup", status_code=303)
            return set_flash(resp, f"Backup restaurado correctamente: {safe_name}")
        else:
            error_msg = result.stderr.decode("utf-8", errors="replace")[:200]
            resp = RedirectResponse("/backup", status_code=303)
            return set_flash(resp, f"Error en psql: {error_msg}", "error")
    except FileNotFoundError:
        # psql no disponible, intentar restauracion por SQLAlchemy
        pass
    except subprocess.TimeoutExpired:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "La restauracion tardo demasiado (timeout)", "error")

    # Fallback: ejecutar SQL directamente con SQLAlchemy
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Filtrar comentarios y lineas vacias, ejecutar statements
        statements = []
        current = []
        for line in sql_content.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            current.append(line)
            if stripped.endswith(";"):
                statements.append("\n".join(current))
                current = []

        executed = 0
        errors = 0
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                db.execute(text(stmt))
                executed += 1
            except Exception:
                errors += 1
                db.rollback()

        db.commit()

        ip = request.client.host if request.client else ""
        log_audit(db, current_user, "UPDATE", "backup", None,
                  f"Backup restaurado (fallback): {safe_name} ({executed} sentencias, {errors} errores)", ip)

        msg = f"Backup restaurado: {executed} sentencias ejecutadas"
        if errors > 0:
            msg += f", {errors} con errores"
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, msg)

    except Exception as e:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, f"Error al restaurar: {type(e).__name__}: {str(e)[:150]}", "error")


@router.post("/eliminar/{filename}")
def eliminar_backup_local(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".sql"):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Archivo no valido", "error")

    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.isfile(filepath):
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "Archivo no encontrado", "error")

    os.remove(filepath)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "backup", None,
              f"Backup eliminado: {safe_name}", ip)

    resp = RedirectResponse("/backup", status_code=303)
    return set_flash(resp, f"Backup eliminado: {safe_name}")
