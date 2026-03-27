from fastapi import APIRouter, Request, Depends, Form
from templates_config import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_auth, log_audit, get_local_id
import models

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("")
def lista_categorias(request: Request, db: Session = Depends(get_db),
                     buscar: str = None, msg: str = None, error: str = None):
    local_id = get_local_id(request)
    query = db.query(models.Categoria).filter(models.Categoria.activo == True)
    if local_id is not None:
        query = query.filter(models.Categoria.local_id == local_id)
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
    local_id = get_local_id(request)
    existe_query = db.query(models.Categoria).filter(models.Categoria.nombre == nombre)
    if local_id is not None:
        existe_query = existe_query.filter(models.Categoria.local_id == local_id)
    existe = existe_query.first()
    if existe:
        return RedirectResponse(f"/categorias?error=Ya+existe+una+categoría+con+ese+nombre", status_code=303)

    cat = models.Categoria(nombre=nombre.strip(), descripcion=descripcion.strip())
    cat.local_id = local_id
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
    local_id = get_local_id(request)
    query = db.query(models.Categoria).filter(models.Categoria.id == cat_id)
    if local_id is not None:
        query = query.filter(models.Categoria.local_id == local_id)
    cat = query.first()
    if not cat:
        return RedirectResponse("/categorias?error=Categoría+no+encontrada", status_code=303)

    existe_query = db.query(models.Categoria).filter(
        models.Categoria.nombre == nombre,
        models.Categoria.id != cat_id
    )
    if local_id is not None:
        existe_query = existe_query.filter(models.Categoria.local_id == local_id)
    existe = existe_query.first()
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
    local_id = get_local_id(request)
    query = db.query(models.Categoria).filter(models.Categoria.id == cat_id)
    if local_id is not None:
        query = query.filter(models.Categoria.local_id == local_id)
    cat = query.first()
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
