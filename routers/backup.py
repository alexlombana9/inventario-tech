import os
import io
import shutil
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db, SQLALCHEMY_DATABASE_URL
from templates_config import templates
from auth import require_role, log_audit
import models

router = APIRouter(prefix="/backup", tags=["backup"])

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inventario.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")


@router.get("")
def backup_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    msg: str = None,
    error: str = None,
):
    # List existing backups
    backups = []
    if os.path.exists(BACKUP_DIR):
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith(".db"):
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
    if not os.path.exists(DB_PATH):
        return RedirectResponse("/backup?error=Base+de+datos+no+encontrada", status_code=303)

    # Use SQLite backup API for consistency
    buffer = io.BytesIO()
    src = sqlite3.connect(DB_PATH)
    dest = sqlite3.connect(":memory:")
    src.backup(dest)
    src.close()

    # Dump memory DB to buffer
    for line in dest.iterdump():
        buffer.write(f"{line}\n".encode("utf-8"))
    dest.close()

    # Actually, let's just copy the file safely
    buffer = io.BytesIO()
    src = sqlite3.connect(DB_PATH)
    backup_conn = sqlite3.connect("")  # in-memory
    src.backup(backup_conn)
    src.close()

    # Serialize to bytes
    temp_path = os.path.join(BACKUP_DIR or ".", f"_temp_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
    os.makedirs(os.path.dirname(temp_path) if os.path.dirname(temp_path) else ".", exist_ok=True)

    # Simpler approach: checkpoint WAL then copy file
    src = sqlite3.connect(DB_PATH)
    src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    src.close()

    with open(DB_PATH, "rb") as f:
        content = f.read()

    buffer = io.BytesIO(content)
    buffer.seek(0)

    filename = f"techstock_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "backup", None, f"Backup descargado: {filename}", ip)

    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/crear")
def crear_backup_local(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    os.makedirs(BACKUP_DIR, exist_ok=True)

    filename = f"techstock_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    dest_path = os.path.join(BACKUP_DIR, filename)

    # Checkpoint WAL and copy
    src = sqlite3.connect(DB_PATH)
    src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    src.close()

    shutil.copy2(DB_PATH, dest_path)

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "backup", None, f"Backup local creado: {filename}", ip)

    return RedirectResponse(f"/backup?msg=Backup+creado:+{filename}", status_code=303)
