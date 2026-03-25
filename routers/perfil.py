import os
import uuid
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from templates_config import templates
from auth import require_auth, hash_password, verify_password, set_flash, log_audit, COOKIE_NAME, get_saved_accounts
import models

router = APIRouter(prefix="/perfil", tags=["perfil"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "avatars")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB


@router.get("")
def perfil_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    saved_accounts = get_saved_accounts(request)
    return templates.TemplateResponse("perfil/index.html", {
        "request": request,
        "usuario": current_user,
        "saved_accounts": saved_accounts,
    })


@router.post("")
def actualizar_perfil(
    request: Request,
    nombre_completo: str = Form(...),
    email: str = Form(""),
    telefono: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    nombre_clean = nombre_completo.strip()
    if not nombre_clean:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "El nombre completo es obligatorio", "error")

    # Re-query user in current db session to ensure changes persist
    user = db.query(models.Usuario).filter(models.Usuario.id == current_user.id).first()
    user.nombre_completo = nombre_clean
    user.email = email.strip()
    user.telefono = telefono.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "UPDATE", "perfil", user.id,
              "Perfil actualizado", ip)

    resp = RedirectResponse("/perfil", status_code=303)
    return set_flash(resp, "Perfil actualizado correctamente")


@router.post("/foto")
async def subir_foto(
    request: Request,
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    # Validar extension
    ext = os.path.splitext(foto.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "Formato no permitido. Usa JPG, PNG, GIF o WebP.", "error")

    # Leer contenido y validar tamano
    content = await foto.read()
    if len(content) > MAX_FILE_SIZE:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "La imagen no puede superar 2 MB.", "error")

    # Crear directorio si no existe
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Re-query user in current db session to ensure changes persist
    user = db.query(models.Usuario).filter(models.Usuario.id == current_user.id).first()

    # Eliminar foto anterior si existe
    if user.foto:
        old_path = os.path.join(UPLOAD_DIR, user.foto)
        if os.path.isfile(old_path):
            os.remove(old_path)

    # Guardar con nombre unico
    filename = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    user.foto = filename
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "UPDATE", "perfil", user.id,
              "Foto de perfil actualizada", ip)

    resp = RedirectResponse("/perfil", status_code=303)
    return set_flash(resp, "Foto de perfil actualizada correctamente")


@router.post("/foto/eliminar")
def eliminar_foto(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    # Re-query user in current db session
    user = db.query(models.Usuario).filter(models.Usuario.id == current_user.id).first()

    if user.foto:
        old_path = os.path.join(UPLOAD_DIR, user.foto)
        if os.path.isfile(old_path):
            os.remove(old_path)
        user.foto = ""
        db.commit()

        ip = request.client.host if request.client else ""
        log_audit(db, user, "UPDATE", "perfil", user.id,
                  "Foto de perfil eliminada", ip)

    resp = RedirectResponse("/perfil", status_code=303)
    return set_flash(resp, "Foto de perfil eliminada")


@router.post("/password")
def cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirmar: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    if not verify_password(password_actual, current_user.password_hash):
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "La contrasena actual es incorrecta", "error")

    if len(password_nueva) < 8:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "La nueva contrasena debe tener al menos 8 caracteres", "error")

    if password_nueva != password_confirmar:
        resp = RedirectResponse("/perfil", status_code=303)
        return set_flash(resp, "Las contrasenas nuevas no coinciden", "error")

    # Re-query user in current db session
    user = db.query(models.Usuario).filter(models.Usuario.id == current_user.id).first()
    user.password_hash = hash_password(password_nueva)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, user, "UPDATE", "perfil", user.id,
              "Contrasena cambiada", ip)

    resp = RedirectResponse("/perfil", status_code=303)
    return set_flash(resp, "Contrasena cambiada correctamente")
