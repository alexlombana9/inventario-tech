import os
import shutil
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from templates_config import templates
from auth import require_role, log_audit, get_local_id
import models

router = APIRouter(prefix="/configuracion", tags=["configuracion"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")


def _get_config(db: Session, local_id: int = None) -> models.Configuracion:
    query = db.query(models.Configuracion)
    if local_id is not None:
        query = query.filter(models.Configuracion.local_id == local_id)
    config = query.first()
    if not config:
        config = models.Configuracion(local_id=local_id)
        db.add(config)
        db.commit()
    return config


@router.get("")
def configuracion_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    msg: str = None,
    error: str = None,
):
    local_id = get_local_id(request)
    config = _get_config(db, local_id=local_id)
    return templates.TemplateResponse("configuracion/form.html", {
        "request": request,
        "config": config,
        "msg": msg,
        "error": error,
    })


@router.post("")
def guardar_configuracion(
    request: Request,
    nombre_negocio: str = Form("TechStock"),
    nit: str = Form(""),
    direccion: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    moneda_simbolo: str = Form("$"),
    moneda_codigo: str = Form("COP"),
    mensaje_recibo: str = Form(""),
    pie_factura: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    local_id = get_local_id(request)
    config = _get_config(db, local_id=local_id)
    config.nombre_negocio = nombre_negocio.strip() or "TechStock"
    config.nit = nit.strip()
    config.direccion = direccion.strip()
    config.telefono = telefono.strip()
    config.email = email.strip()
    config.moneda_simbolo = moneda_simbolo.strip() or "$"
    config.moneda_codigo = moneda_codigo.strip() or "COP"
    config.mensaje_recibo = mensaje_recibo.strip()
    config.pie_factura = pie_factura.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "configuracion", config.id, "Configuración actualizada", ip)

    return RedirectResponse("/configuracion?msg=Configuración+guardada+correctamente", status_code=303)


@router.post("/logo")
async def subir_logo(
    request: Request,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    if not logo.filename:  # pragma: no cover — FastAPI returns 422 before reaching this
        return RedirectResponse("/configuracion?error=No+se+seleccionó+archivo", status_code=303)

    ext = os.path.splitext(logo.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        return RedirectResponse("/configuracion?error=Solo+se+permiten+imágenes+PNG,+JPG+o+WebP", status_code=303)

    content = await logo.read()
    if len(content) > 2 * 1024 * 1024:
        return RedirectResponse("/configuracion?error=La+imagen+no+debe+superar+2MB", status_code=303)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"logo{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    local_id = get_local_id(request)
    config = _get_config(db, local_id=local_id)
    config.logo_path = f"/static/uploads/{filename}"
    db.commit()

    return RedirectResponse("/configuracion?msg=Logo+actualizado+correctamente", status_code=303)
