from fastapi import APIRouter, Request, Depends, Form
from templates_config import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_auth, log_audit
import models

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("")
def lista_categorias(request: Request, db: Session = Depends(get_db),
                     buscar: str = None, msg: str = None, error: str = None):
    query = db.query(models.Categoria).filter(models.Categoria.activo == True)
    if buscar:
        query = query.filter(
            models.Categoria.nombre.ilike(f"%{buscar}%") |
            models.Categoria.descripcion.ilike(f"%{buscar}%")
        )
    categorias = query.order_by(models.Categoria.nombre).all()
    return templates.TemplateResponse("categorias/lista.html", {
        "request": request,
        "categorias": categorias,
        "buscar": buscar or "",
        "msg": msg,
        "error": error,
    })


@router.post("/nueva")
def crear_categoria(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    existe = db.query(models.Categoria).filter(models.Categoria.nombre == nombre).first()
    if existe:
        return RedirectResponse(f"/categorias?error=Ya+existe+una+categoría+con+ese+nombre", status_code=303)

    cat = models.Categoria(nombre=nombre.strip(), descripcion=descripcion.strip())
    db.add(cat)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "categoria", cat.id,
              f"Categoría creada: {cat.nombre}", ip)

    return RedirectResponse("/categorias?msg=Categoría+creada+correctamente", status_code=303)


@router.post("/{cat_id}/editar")
def editar_categoria(
    cat_id: int,
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    cat = db.query(models.Categoria).filter(models.Categoria.id == cat_id).first()
    if not cat:
        return RedirectResponse("/categorias?error=Categoría+no+encontrada", status_code=303)

    existe = db.query(models.Categoria).filter(
        models.Categoria.nombre == nombre,
        models.Categoria.id != cat_id
    ).first()
    if existe:
        return RedirectResponse(f"/categorias?error=Ya+existe+una+categoría+con+ese+nombre", status_code=303)

    cat.nombre = nombre.strip()
    cat.descripcion = descripcion.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "categoria", cat.id,
              f"Categoría actualizada: {cat.nombre}", ip)

    return RedirectResponse("/categorias?msg=Categoría+actualizada", status_code=303)


@router.post("/{cat_id}/eliminar")
def eliminar_categoria(cat_id: int, request: Request, db: Session = Depends(get_db),
                       current_user: models.Usuario = Depends(require_auth)):
    cat = db.query(models.Categoria).filter(models.Categoria.id == cat_id).first()
    if not cat:
        return RedirectResponse("/categorias?error=Categoría+no+encontrada", status_code=303)

    tiene_productos = db.query(models.Producto).filter(
        models.Producto.categoria_id == cat_id,
        models.Producto.activo == True,
    ).count()
    if tiene_productos > 0:
        return RedirectResponse(
            f"/categorias?error=No+se+puede+eliminar,+tiene+{tiene_productos}+producto(s)+activo(s)+asociado(s)",
            status_code=303
        )

    cat.activo = False
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "categoria", cat.id,
              f"Categoría desactivada: {cat.nombre}", ip)

    return RedirectResponse("/categorias?msg=Categoría+eliminada", status_code=303)
