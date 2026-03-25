from typing import List
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from templates_config import templates
from auth import require_role, hash_password, set_flash, log_audit, MODULOS_DISPONIBLES, PERMISOS_POR_ROL, get_user_permisos
import models

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

ROLES = [
    ("ADMIN", "Administrador"),
    ("VENDEDOR", "Vendedor"),
    ("BODEGUERO", "Bodeguero"),
]


@router.get("")
def lista_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    buscar: str = None,
    rol: str = None,
    estado: str = None,
    msg: str = None,
    error: str = None,
):
    query = db.query(models.Usuario)
    if buscar:
        query = query.filter(
            models.Usuario.nombre_completo.ilike(f"%{buscar}%") |
            models.Usuario.username.ilike(f"%{buscar}%") |
            models.Usuario.email.ilike(f"%{buscar}%")
        )
    if rol and rol.strip():
        query = query.filter(models.Usuario.rol == rol)
    if estado and estado.strip():
        if estado == "activo":
            query = query.filter(models.Usuario.activo == True)
        elif estado == "inactivo":
            query = query.filter(models.Usuario.activo == False)
    usuarios = query.order_by(models.Usuario.nombre_completo).all()

    return templates.TemplateResponse("usuarios/lista.html", {
        "request": request,
        "usuarios": usuarios,
        "buscar": buscar or "",
        "rol": rol or "",
        "estado": estado or "",
        "roles": ROLES,
        "msg": msg,
        "error": error,
    })


@router.get("/nuevo")
def nuevo_usuario_form(
    request: Request,
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    error: str = None,
):
    return templates.TemplateResponse("usuarios/form.html", {
        "request": request,
        "usuario": None,
        "roles": ROLES,
        "accion": "Nuevo",
        "error": error,
        "modulos_disponibles": MODULOS_DISPONIBLES,
        "permisos_por_rol": PERMISOS_POR_ROL,
        "permisos_usuario": [],
    })


@router.post("/nuevo")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    nombre_completo: str = Form(...),
    rol: str = Form("VENDEDOR"),
    permisos: List[str] = Form([]),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    username_clean = username.strip().lower()

    existe = db.query(models.Usuario).filter(
        models.Usuario.username == username_clean
    ).first()
    if existe:
        return RedirectResponse(
            f"/usuarios/nuevo?error=Ya+existe+un+usuario+con+el+nombre+{username_clean}",
            status_code=303
        )

    if len(password) < 8:
        return RedirectResponse(
            "/usuarios/nuevo?error=La+contrasena+debe+tener+al+menos+8+caracteres",
            status_code=303
        )

    # Determinar permisos: si son los mismos del rol por defecto, guardar vacio
    permisos_default = set(PERMISOS_POR_ROL.get(rol, []))
    permisos_set = set(permisos)
    permisos_str = ",".join(sorted(permisos)) if permisos_set != permisos_default else ""

    usuario = models.Usuario(
        username=username_clean,
        password_hash=hash_password(password),
        nombre_completo=nombre_completo.strip(),
        rol=rol,
        permisos=permisos_str,
        activo=True,
    )
    db.add(usuario)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "usuario", usuario.id,
              f"Usuario creado: {usuario.username} ({usuario.rol})", ip)

    return RedirectResponse("/usuarios?msg=Usuario+creado+correctamente", status_code=303)


@router.get("/{user_id}/editar")
def editar_usuario_form(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    error: str = None,
):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not usuario:
        return RedirectResponse("/usuarios?error=Usuario+no+encontrado", status_code=303)

    return templates.TemplateResponse("usuarios/form.html", {
        "request": request,
        "usuario": usuario,
        "roles": ROLES,
        "accion": "Editar",
        "error": error,
        "modulos_disponibles": MODULOS_DISPONIBLES,
        "permisos_por_rol": PERMISOS_POR_ROL,
        "permisos_usuario": get_user_permisos(usuario),
    })


@router.post("/{user_id}/editar")
def actualizar_usuario(
    user_id: int,
    request: Request,
    nombre_completo: str = Form(...),
    rol: str = Form("VENDEDOR"),
    password: str = Form(""),
    activo: str = Form("on"),
    permisos: List[str] = Form([]),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not usuario:
        return RedirectResponse("/usuarios?error=Usuario+no+encontrado", status_code=303)

    # No permitir desactivar al propio admin
    if usuario.id == current_user.id and activo != "on":
        return RedirectResponse(
            f"/usuarios/{user_id}/editar?error=No+puedes+desactivar+tu+propia+cuenta",
            status_code=303
        )

    usuario.nombre_completo = nombre_completo.strip()
    usuario.rol = rol
    usuario.activo = (activo == "on")

    if password and len(password) >= 8:
        usuario.password_hash = hash_password(password)

    # Guardar permisos personalizados (vacio = usar default del rol)
    permisos_default = set(PERMISOS_POR_ROL.get(rol, []))
    permisos_set = set(permisos)
    usuario.permisos = ",".join(sorted(permisos)) if permisos_set != permisos_default else ""

    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "usuario", usuario.id,
              f"Usuario actualizado: {usuario.username}", ip)

    return RedirectResponse("/usuarios?msg=Usuario+actualizado+correctamente", status_code=303)


@router.post("/{user_id}/eliminar")
def eliminar_usuario(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not usuario:
        return RedirectResponse("/usuarios?error=Usuario+no+encontrado", status_code=303)

    if usuario.id == current_user.id:
        return RedirectResponse("/usuarios?error=No+puedes+eliminar+tu+propia+cuenta", status_code=303)

    usuario.activo = False
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "DELETE", "usuario", usuario.id,
              f"Usuario desactivado: {usuario.username}", ip)

    return RedirectResponse("/usuarios?msg=Usuario+desactivado+correctamente", status_code=303)
