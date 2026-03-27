from fastapi import APIRouter, Request, Depends, Form
from templates_config import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_auth, log_audit
import models

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


@router.get("")
def lista_proveedores(request: Request, db: Session = Depends(get_db),
                      buscar: str = None, msg: str = None, error: str = None):
    query = db.query(models.Proveedor).filter(models.Proveedor.activo == True)
    if buscar:
        query = query.filter(
            models.Proveedor.nombre.ilike(f"%{buscar}%") |
            models.Proveedor.contacto.ilike(f"%{buscar}%") |
            models.Proveedor.telefono.ilike(f"%{buscar}%") |
            models.Proveedor.email.ilike(f"%{buscar}%") |
            models.Proveedor.nit_ruc.ilike(f"%{buscar}%")
        )
    proveedores = query.order_by(models.Proveedor.nombre).all()
    return templates.TemplateResponse("proveedores/lista.html", {
        "request": request,
        "proveedores": proveedores,
        "buscar": buscar or "",
        "msg": msg,
        "error": error,
    })


@router.get("/nuevo")
def nuevo_proveedor_form(request: Request):
    return templates.TemplateResponse("proveedores/form.html", {
        "request": request,
        "proveedor": None,
        "accion": "Nuevo",
    })


@router.post("/nuevo")
def crear_proveedor(
    request: Request,
    nombre: str = Form(...),
    contacto: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
    nit_ruc: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    prov = models.Proveedor(
        nombre=nombre.strip(),
        contacto=contacto.strip(),
        telefono=telefono.strip(),
        email=email.strip(),
        direccion=direccion.strip(),
        nit_ruc=nit_ruc.strip(),
    )
    db.add(prov)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "proveedor", prov.id,
              f"Proveedor creado: {nombre.strip()}", ip)

    return RedirectResponse("/proveedores?msg=Proveedor+creado+correctamente", status_code=303)


@router.get("/{prov_id}/editar")
def editar_proveedor_form(prov_id: int, request: Request, db: Session = Depends(get_db)):
    prov = db.query(models.Proveedor).filter(models.Proveedor.id == prov_id).first()
    if not prov:
        return RedirectResponse("/proveedores?error=Proveedor+no+encontrado", status_code=303)
    return templates.TemplateResponse("proveedores/form.html", {
        "request": request,
        "proveedor": prov,
        "accion": "Editar",
    })


@router.post("/{prov_id}/editar")
def actualizar_proveedor(
    prov_id: int,
    request: Request,
    nombre: str = Form(...),
    contacto: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
    nit_ruc: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    prov = db.query(models.Proveedor).filter(models.Proveedor.id == prov_id).first()
    if not prov:
        return RedirectResponse("/proveedores?error=Proveedor+no+encontrado", status_code=303)

    prov.nombre = nombre.strip()
    prov.contacto = contacto.strip()
    prov.telefono = telefono.strip()
    prov.email = email.strip()
    prov.direccion = direccion.strip()
    prov.nit_ruc = nit_ruc.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "proveedor", prov_id,
              f"Proveedor actualizado: {nombre.strip()}", ip)

    return RedirectResponse("/proveedores?msg=Proveedor+actualizado+correctamente", status_code=303)


@router.post("/{prov_id}/eliminar")
def eliminar_proveedor(prov_id: int, request: Request,
                       db: Session = Depends(get_db),
                       current_user: models.Usuario = Depends(require_auth)):
    prov = db.query(models.Proveedor).filter(models.Proveedor.id == prov_id).first()
    if not prov:
        return RedirectResponse("/proveedores?error=Proveedor+no+encontrado", status_code=303)
    prov.activo = False
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "proveedor", prov_id,
              f"Proveedor desactivado: {prov.nombre}", ip)

    return RedirectResponse("/proveedores?msg=Proveedor+desactivado+correctamente", status_code=303)


@router.get("/{prov_id}/detalle")
def detalle_proveedor(prov_id: int, request: Request, db: Session = Depends(get_db)):
    prov = db.query(models.Proveedor).filter(models.Proveedor.id == prov_id).first()
    if not prov:
        return RedirectResponse("/proveedores?error=Proveedor+no+encontrado", status_code=303)

    movimientos = db.query(models.MovimientoInventario).filter(
        models.MovimientoInventario.proveedor_id == prov_id
    ).order_by(models.MovimientoInventario.fecha.desc()).limit(20).all()

    productos = db.query(models.Producto).filter(
        models.Producto.proveedor_id == prov_id,
        models.Producto.activo == True
    ).all()

    return templates.TemplateResponse("proveedores/detalle.html", {
        "request": request,
        "proveedor": prov,
        "movimientos": movimientos,
        "productos": productos,
    })
