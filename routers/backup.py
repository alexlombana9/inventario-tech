import os
import io
import subprocess
import tempfile
from datetime import datetime
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, DATABASE_URL
from templates_config import templates
from auth import require_role, require_superadmin, set_flash, log_audit
import models

router = APIRouter(prefix="/backup", tags=["backup"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
MAX_BACKUP_SIZE = 50 * 1024 * 1024  # 50 MB

# Tablas en orden de dependencia (hijos primero para TRUNCATE, padres primero para INSERT)
_TABLES_INSERT_ORDER = [
    "locales", "usuarios", "categorias", "proveedores", "productos",
    "clientes", "acreedores", "cajas",
    "movimientos_inventario", "ventas", "detalle_venta",
    "movimientos_caja", "deudas", "pagos_deuda",
    "facturas", "cobros_factura", "gastos", "configuracion", "audit_log",
]


def _parse_pg_url(url: str) -> dict:
    """Extrae host, port, dbname, user, password de la DATABASE_URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 5432),
        "dbname": (parsed.path or "/inventario").lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def _find_pg_binary(name: str) -> str:
    """Busca binario PG en portable pgsql/bin/ o en PATH."""
    ext = ".exe" if os.name == "nt" else ""
    portable = os.path.join(PROJECT_ROOT, "pgsql", "bin", f"{name}{ext}")
    if os.path.isfile(portable):
        return portable
    return name


def _pg_env(pg: dict) -> dict:
    """Crea entorno con PGPASSWORD para subprocesos PG."""
    env = os.environ.copy()
    if pg["password"]:
        env["PGPASSWORD"] = pg["password"]
    return env


def _pg_dump_sql(pg: dict) -> bytes | None:
    """Intenta ejecutar pg_dump y retorna los bytes del dump, o None si falla."""
    pg_dump = _find_pg_binary("pg_dump")
    try:
        result = subprocess.run(
            [
                pg_dump,
                "-h", pg["host"],
                "-p", pg["port"],
                "-U", pg["user"],
                "-d", pg["dbname"],
                "--no-owner",
                "--no-acl",
                "--data-only",
                "--inserts",
            ],
            capture_output=True,
            env=_pg_env(pg),
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _fallback_dump(db: Session) -> bytes:
    """Genera un dump SQL completo usando SQLAlchemy (cuando pg_dump no esta disponible)."""
    lines = [
        f"-- TechStock Backup",
        f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"-- Formato: INSERT (compatible con psql y SQLAlchemy)",
        "",
    ]

    # Whitelist de tablas validas
    valid_tables = set(_TABLES_INSERT_ORDER)

    for table_name in _TABLES_INSERT_ORDER:
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

            lines.append(f"-- Tabla: {table_name} ({len(rows)} registros)")
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
            lines.append("")
        except Exception as e:
            lines.append(f"-- Error exportando tabla {table_name}: {type(e).__name__}")

    return "\n".join(lines).encode("utf-8")


def _restore_with_psql(filepath: str, pg: dict) -> tuple[bool, str]:
    """Restaura usando psql. Retorna (exito, mensaje).

    Usa --single-transaction para atomicidad: si algo falla, todo hace rollback.
    Deshabilita triggers FK para tolerar INSERTs en cualquier orden.
    No requiere permisos de superuser (el owner de las tablas puede hacerlo).
    """
    psql = _find_pg_binary("psql")

    # Leer el dump para analizar su contenido
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        dump_content = f.read()

    # Construir SQL de restauracion atomica
    restore_lines = []

    # Deshabilitar triggers FK en todas las tablas (permite INSERTs en cualquier orden)
    for table in _TABLES_INSERT_ORDER:
        restore_lines.append(f"ALTER TABLE {table} DISABLE TRIGGER ALL;")

    # Limpiar TODAS las tablas de una vez (CASCADE maneja FK automaticamente)
    has_truncate = "TRUNCATE" in dump_content
    if not has_truncate:
        all_tables = ", ".join(reversed(_TABLES_INSERT_ORDER))
        restore_lines.append(f"TRUNCATE TABLE {all_tables} CASCADE;")

    # Agregar el contenido del dump (INSERTs — orden no importa con triggers deshabilitados)
    restore_lines.append("")
    restore_lines.append(dump_content)
    restore_lines.append("")

    # Re-habilitar triggers FK
    for table in _TABLES_INSERT_ORDER:
        restore_lines.append(f"ALTER TABLE {table} ENABLE TRIGGER ALL;")

    # Resetear secuencias de IDs para que nuevos registros no colisionen
    for table in _TABLES_INSERT_ORDER:
        restore_lines.append(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false) "
            f"WHERE pg_get_serial_sequence('{table}', 'id') IS NOT NULL;"
        )

    restore_sql = "\n".join(restore_lines)

    # Escribir a archivo temporal
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sql", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(restore_sql)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                psql,
                "-h", pg["host"],
                "-p", pg["port"],
                "-U", pg["user"],
                "-d", pg["dbname"],
                "-v", "ON_ERROR_STOP=1",
                "--single-transaction",
                "-f", tmp_path,
            ],
            capture_output=True,
            env=_pg_env(pg),
            timeout=300,
        )
    finally:
        os.unlink(tmp_path)

    if result.returncode == 0:
        return True, "OK"
    else:
        stderr = result.stderr.decode("utf-8", errors="replace")
        # Filtrar lineas informativas de psql, mantener solo errores reales
        error_lines = [
            l for l in stderr.split("\n")
            if l.strip() and "ERROR" in l.upper()
        ]
        error_msg = "; ".join(error_lines[:3]) if error_lines else stderr[:300]
        return False, error_msg


def _restore_with_sqlalchemy(filepath: str, db: Session) -> tuple[bool, str]:
    """Restaura usando SQLAlchemy. Todo en UNA transaccion (atomico).

    Si algo falla, hace ROLLBACK completo y la DB queda intacta.
    Deshabilita FK constraints para tolerar INSERTs en cualquier orden.
    No requiere permisos de superuser.
    """
    is_pg = DATABASE_URL.startswith("postgresql")

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        sql_content = f.read()

    # Verificar que el dump contiene INSERT statements
    has_inserts = "INSERT INTO" in sql_content.upper()
    has_copy = "COPY " in sql_content and "FROM stdin" in sql_content
    if not has_inserts and has_copy:
        return False, (
            "El backup usa formato COPY (incompatible sin psql). "
            "Instale PostgreSQL completo o use un backup en formato INSERT."
        )
    if not has_inserts and not has_copy:
        return False, "El archivo no contiene datos para restaurar."

    # Parsear statements SQL (solo INSERT y comandos ejecutables)
    statements = []
    current = []
    for line in sql_content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        # Saltar comandos que SQLAlchemy no puede ejecutar
        upper = stripped.upper()
        if any(upper.startswith(skip) for skip in [
            "COPY ", "\\.", "CREATE ", "DROP ", "ALTER ", "GRANT ", "REVOKE ",
            "SET DEFAULT_", "SET STATEMENT_", "SET LOCK_", "SET CLIENT_",
            "SET SEARCH_PATH", "SET CHECK_", "SET XMLOPTION",
            "SET SESSION", "SELECT PG_CATALOG",
        ]):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []

    # Restaurar en UNA transaccion atomica
    try:
        # Deshabilitar FK constraints (permite INSERTs en cualquier orden)
        if is_pg:
            for table in _TABLES_INSERT_ORDER:
                db.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER ALL"))
        else:
            db.execute(text("PRAGMA foreign_keys = OFF"))

        # Limpiar tablas (una sola sentencia en PG, loop en SQLite)
        if is_pg:
            all_tables = ", ".join(reversed(_TABLES_INSERT_ORDER))
            db.execute(text(f"TRUNCATE TABLE {all_tables} CASCADE"))
        else:
            for table in reversed(_TABLES_INSERT_ORDER):
                db.execute(text(f"DELETE FROM {table}"))

        # Ejecutar todos los INSERT statements
        executed = 0
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            db.execute(text(stmt))
            executed += 1

        # Re-habilitar FK constraints
        if is_pg:
            for table in _TABLES_INSERT_ORDER:
                db.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER ALL"))
        else:
            db.execute(text("PRAGMA foreign_keys = ON"))

        # Resetear secuencias (solo PostgreSQL)
        if is_pg:
            for table in _TABLES_INSERT_ORDER:
                db.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false) "
                    f"WHERE pg_get_serial_sequence('{table}', 'id') IS NOT NULL"
                ))

        # COMMIT solo si todo salio bien
        db.commit()
        return True, f"{executed} sentencias ejecutadas"

    except Exception as e:
        # ROLLBACK atomico: la DB queda intacta como antes
        # (en PG el DISABLE TRIGGER tambien se revierte con el rollback)
        db.rollback()
        # Re-habilitar FK en SQLite (PRAGMA no es transaccional)
        if not is_pg:
            try:
                db.execute(text("PRAGMA foreign_keys = ON"))
            except Exception:
                pass
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        return False, error_msg


@router.get("")
def backup_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
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
    current_user: models.Usuario = Depends(require_superadmin),
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
    current_user: models.Usuario = Depends(require_superadmin),
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
    current_user: models.Usuario = Depends(require_superadmin),
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
    if not safe_name.endswith(".sql"):  # pragma: no cover
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
    current_user: models.Usuario = Depends(require_superadmin),
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
    current_user: models.Usuario = Depends(require_superadmin),
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

    # Paso 1: Intentar restaurar con psql (maneja cualquier formato, atomico)
    try:
        ok, msg = _restore_with_psql(filepath, pg)
        if ok:
            try:
                ip = request.client.host if request.client else ""
                log_audit(db, current_user, "UPDATE", "backup", None,
                          f"Backup restaurado (psql): {safe_name}", ip)
            except Exception:
                pass  # DB cambio tras restore, audit puede fallar
            resp = RedirectResponse("/backup", status_code=303)
            return set_flash(resp, f"Backup restaurado correctamente: {safe_name}")
        else:
            resp = RedirectResponse("/backup", status_code=303)
            return set_flash(resp, f"Error en restauracion: {msg}", "error")
    except FileNotFoundError:
        pass  # psql no disponible, usar fallback
    except subprocess.TimeoutExpired:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, "La restauracion tardo demasiado (timeout)", "error")
    except Exception as e:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, f"Error leyendo backup: {type(e).__name__}: {str(e)[:150]}", "error")

    # Paso 2: Fallback con SQLAlchemy (solo dumps con INSERT, atomico)
    try:
        ok, msg = _restore_with_sqlalchemy(filepath, db)
    except Exception as e:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, f"Error al restaurar: {type(e).__name__}: {str(e)[:150]}", "error")

    if ok:
        try:
            ip = request.client.host if request.client else ""
            log_audit(db, current_user, "UPDATE", "backup", None,
                      f"Backup restaurado (SQLAlchemy): {safe_name} — {msg}", ip)
        except Exception:
            pass  # DB cambio tras restore, audit puede fallar
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, f"Backup restaurado correctamente: {safe_name}")
    else:
        resp = RedirectResponse("/backup", status_code=303)
        return set_flash(resp, f"Error al restaurar: {msg}", "error")


@router.post("/eliminar/{filename}")
def eliminar_backup_local(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
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
