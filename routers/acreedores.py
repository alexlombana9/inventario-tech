from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
from auth import require_auth, log_audit
import models

router = APIRouter(prefix="/acreedores", tags=["acreedores"])

from utils.constants import TIPOS_ACREEDOR


@router.get("")
def lista_acreedores(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    buscar: str = None,
    tipo: str = None,
    msg: str = None,
    error: str = None,
):
    query = db.query(models.Acreedor).filter(models.Acreedor.activo == True)
    if buscar:
        term = f"%{buscar}%"
        query = query.filter(
            models.Acreedor.nombre.ilike(term)
            | models.Acreedor.documento.ilike(term)
            | models.Acreedor.telefono.ilike(term)
            | models.Acreedor.email.ilike(term)
        )
    if tipo:
        query = query.filter(models.Acreedor.tipo == tipo)
    acreedores = query.order_by(models.Acreedor.nombre).all()

    return templates.TemplateResponse("acreedores/lista.html", {
        "request": request,
        "acreedores": acreedores,
        "buscar": buscar or "",
        "tipo": tipo or "",
        "tipos_acreedor": TIPOS_ACREEDOR,
        "msg": msg,
        "error": error,
    })


@router.get("/nuevo")
def nuevo_acreedor_form(
    request: Request,
    current_user: models.Usuario = Depends(require_auth),
):
    return templates.TemplateResponse("acreedores/form.html", {
        "request": request,
        "acreedor": None,
        "tipos_acreedor": TIPOS_ACREEDOR,
        "accion": "Nuevo",
    })


@router.post("/nuevo")
def crear_acreedor(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form("OTRO"),
    documento: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    acreedor = models.Acreedor(
        nombre=nombre.strip(),
        tipo=tipo,
        documento=documento.strip(),
        telefono=telefono.strip(),
        email=email.strip(),
        direccion=direccion.strip(),
        notas=notas.strip(),
    )
    db.add(acreedor)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "acreedor", acreedor.id,
              f"Acreedor creado: {acreedor.nombre}", ip)

    return RedirectResponse("/acreedores?msg=Acreedor+creado+correctamente", status_code=303)


@router.get("/{acreedor_id}/editar")
def editar_acreedor_form(
    acreedor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    acreedor = db.query(models.Acreedor).filter(models.Acreedor.id == acreedor_id).first()
    if not acreedor:
        return RedirectResponse("/acreedores?error=Acreedor+no+encontrado", status_code=303)
    return templates.TemplateResponse("acreedores/form.html", {
        "request": request,
        "acreedor": acreedor,
        "tipos_acreedor": TIPOS_ACREEDOR,
        "accion": "Editar",
    })


@router.post("/{acreedor_id}/editar")
def actualizar_acreedor(
    acreedor_id: int,
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form("OTRO"),
    documento: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    acreedor = db.query(models.Acreedor).filter(models.Acreedor.id == acreedor_id).first()
    if not acreedor:
        return RedirectResponse("/acreedores?error=Acreedor+no+encontrado", status_code=303)

    acreedor.nombre = nombre.strip()
    acreedor.tipo = tipo
    acreedor.documento = documento.strip()
    acreedor.telefono = telefono.strip()
    acreedor.email = email.strip()
    acreedor.direccion = direccion.strip()
    acreedor.notas = notas.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "acreedor", acreedor.id,
              f"Acreedor actualizado: {acreedor.nombre}", ip)

    return RedirectResponse("/acreedores?msg=Acreedor+actualizado+correctamente", status_code=303)


@router.post("/{acreedor_id}/eliminar")
def eliminar_acreedor(
    acreedor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    acreedor = db.query(models.Acreedor).filter(models.Acreedor.id == acreedor_id).first()
    if not acreedor:
        return RedirectResponse("/acreedores?error=Acreedor+no+encontrado", status_code=303)
    acreedor.activo = False
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "acreedor", acreedor.id,
              f"Acreedor desactivado: {acreedor.nombre}", ip)

    return RedirectResponse("/acreedores?msg=Acreedor+desactivado+correctamente", status_code=303)
