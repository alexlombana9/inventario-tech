from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from templates_config import templates
from auth import require_auth, log_audit, get_local_id
import models

router = APIRouter(prefix="/clientes", tags=["clientes"])

TIPOS_DOCUMENTO = ["CC", "NIT", "CE", "PASAPORTE", "TI", "OTRO"]


@router.get("")
def lista_clientes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
    buscar: str = None,
    tipo_documento: str = None,
    msg: str = None,
    error: str = None,
):
    local_id = get_local_id(request)
    query = db.query(models.Cliente).filter(models.Cliente.activo == True)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    if buscar:
        query = query.filter(
            models.Cliente.nombre.ilike(f"%{buscar}%") |
            models.Cliente.empresa.ilike(f"%{buscar}%") |
            models.Cliente.documento.ilike(f"%{buscar}%") |
            models.Cliente.telefono.ilike(f"%{buscar}%") |
            models.Cliente.email.ilike(f"%{buscar}%")
        )
    if tipo_documento and tipo_documento.strip():
        query = query.filter(models.Cliente.tipo_documento == tipo_documento)
    clientes = query.order_by(models.Cliente.nombre).all()

    return templates.TemplateResponse("clientes/lista.html", {
        "request": request,
        "clientes": clientes,
        "buscar": buscar or "",
        "tipo_documento": tipo_documento or "",
        "tipos_documento": TIPOS_DOCUMENTO,
        "msg": msg,
        "error": error,
    })


@router.get("/exportar")
def exportar_clientes(
    request: Request,
    db: Session = Depends(get_db),
    buscar: str = None,
    tipo_documento: str = None,
):
    from utils.excel import generate_excel

    local_id = get_local_id(request)
    query = db.query(models.Cliente).filter(models.Cliente.activo == True)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    if buscar:
        query = query.filter(
            models.Cliente.nombre.ilike(f"%{buscar}%") |
            models.Cliente.empresa.ilike(f"%{buscar}%") |
            models.Cliente.documento.ilike(f"%{buscar}%") |
            models.Cliente.telefono.ilike(f"%{buscar}%") |
            models.Cliente.email.ilike(f"%{buscar}%")
        )
    if tipo_documento and tipo_documento.strip():
        query = query.filter(models.Cliente.tipo_documento == tipo_documento)
    clientes = query.order_by(models.Cliente.nombre).all()

    headers = ["Nombre", "Empresa", "Tipo Doc.", "Documento", "Telefono",
               "Email", "Direccion", "Notas"]
    rows = []
    for c in clientes:
        rows.append([
            c.nombre,
            c.empresa or "",
            c.tipo_documento,
            c.documento or "",
            c.telefono or "",
            c.email or "",
            c.direccion or "",
            c.notas or "",
        ])

    output = generate_excel(
        "Listado de Clientes", headers, rows,
        col_widths=[24, 20, 10, 16, 16, 24, 30, 24],
    )
    filename = f"clientes_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/nuevo")
def nuevo_cliente_form(
    request: Request,
    current_user: models.Usuario = Depends(require_auth),
):
    return templates.TemplateResponse("clientes/form.html", {
        "request": request,
        "cliente": None,
        "tipos_documento": TIPOS_DOCUMENTO,
        "accion": "Nuevo",
    })


@router.post("/nuevo")
def crear_cliente(
    request: Request,
    nombre: str = Form(...),
    empresa: str = Form(""),
    tipo_documento: str = Form("CC"),
    documento: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    cliente = models.Cliente(
        nombre=nombre.strip(),
        empresa=empresa.strip(),
        tipo_documento=tipo_documento,
        documento=documento.strip(),
        telefono=telefono.strip(),
        email=email.strip(),
        direccion=direccion.strip(),
        notas=notas.strip(),
    )
    cliente.local_id = get_local_id(request)
    db.add(cliente)
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "CREATE", "cliente", cliente.id, f"Cliente creado: {cliente.nombre}", ip)

    return RedirectResponse("/clientes?msg=Cliente+creado+correctamente", status_code=303)


@router.get("/{cliente_id}/editar")
def editar_cliente_form(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Cliente).filter(models.Cliente.id == cliente_id)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    cliente = query.first()
    if not cliente:
        return RedirectResponse("/clientes?error=Cliente+no+encontrado", status_code=303)

    return templates.TemplateResponse("clientes/form.html", {
        "request": request,
        "cliente": cliente,
        "tipos_documento": TIPOS_DOCUMENTO,
        "accion": "Editar",
    })


@router.post("/{cliente_id}/editar")
def actualizar_cliente(
    cliente_id: int,
    request: Request,
    nombre: str = Form(...),
    empresa: str = Form(""),
    tipo_documento: str = Form("CC"),
    documento: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Cliente).filter(models.Cliente.id == cliente_id)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    cliente = query.first()
    if not cliente:
        return RedirectResponse("/clientes?error=Cliente+no+encontrado", status_code=303)

    cliente.nombre = nombre.strip()
    cliente.empresa = empresa.strip()
    cliente.tipo_documento = tipo_documento
    cliente.documento = documento.strip()
    cliente.telefono = telefono.strip()
    cliente.email = email.strip()
    cliente.direccion = direccion.strip()
    cliente.notas = notas.strip()
    db.commit()

    ip = request.client.host if request.client else ""
    log_audit(db, current_user, "UPDATE", "cliente", cliente.id, f"Cliente actualizado: {cliente.nombre}", ip)

    return RedirectResponse("/clientes?msg=Cliente+actualizado+correctamente", status_code=303)


@router.get("/{cliente_id}/detalle")
def detalle_cliente(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Cliente).filter(models.Cliente.id == cliente_id)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    cliente = query.first()
    if not cliente:
        return RedirectResponse("/clientes?error=Cliente+no+encontrado", status_code=303)

    ventas_query = db.query(models.Venta).filter(
        models.Venta.cliente_id == cliente_id,
        models.Venta.estado == "COMPLETADA"
    )
    if local_id is not None:
        ventas_query = ventas_query.filter(models.Venta.local_id == local_id)
    ventas = ventas_query.order_by(models.Venta.fecha.desc()).limit(20).all()

    total_compras = sum(v.total for v in ventas)

    return templates.TemplateResponse("clientes/detalle.html", {
        "request": request,
        "cliente": cliente,
        "ventas": ventas,
        "total_compras": total_compras,
    })


@router.post("/{cliente_id}/eliminar")
def eliminar_cliente(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_auth),
):
    local_id = get_local_id(request)
    query = db.query(models.Cliente).filter(models.Cliente.id == cliente_id)
    if local_id is not None:
        query = query.filter(models.Cliente.local_id == local_id)
    cliente = query.first()
    if not cliente:
        return RedirectResponse("/clientes?error=Cliente+no+encontrado", status_code=303)
    cliente.activo = False
    db.commit()
    return RedirectResponse("/clientes?msg=Cliente+desactivado+correctamente", status_code=303)
