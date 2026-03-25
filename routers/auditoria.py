from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta

from database import get_db
from templates_config import templates
from auth import require_role
import models

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("")
def lista_auditoria(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role("ADMIN")),
    buscar: str = None,
    usuario_id: str = None,
    accion: str = None,
    entidad: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    pagina: str = None,
):
    pag = int(pagina) if pagina and pagina.strip() else 1
    por_pagina = 30

    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not fecha_hasta:
        fecha_hasta = date.today().strftime("%Y-%m-%d")

    query = db.query(models.AuditLog)

    # Filtro por fechas
    try:
        fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(models.AuditLog.created_at >= fd, models.AuditLog.created_at <= fh)
    except ValueError:
        pass

    # Filtro por usuario
    if usuario_id and usuario_id.strip():
        try:
            query = query.filter(models.AuditLog.usuario_id == int(usuario_id))
        except ValueError:
            pass

    # Filtro por accion
    if accion and accion.strip():
        query = query.filter(models.AuditLog.accion == accion)

    # Filtro por entidad
    if entidad and entidad.strip():
        query = query.filter(models.AuditLog.entidad == entidad)

    # Busqueda en detalle y nombre de usuario
    if buscar and buscar.strip():
        query = query.filter(
            models.AuditLog.detalle.ilike(f"%{buscar}%") |
            models.AuditLog.usuario_nombre.ilike(f"%{buscar}%") |
            models.AuditLog.ip_address.ilike(f"%{buscar}%")
        )

    total = query.count()
    registros = query.order_by(models.AuditLog.created_at.desc()) \
        .offset((pag - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    # Obtener listas para filtros
    usuarios = db.query(models.Usuario).order_by(models.Usuario.nombre_completo).all()

    acciones_disponibles = ["LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE"]
    entidades_disponibles = [r[0] for r in db.query(models.AuditLog.entidad).distinct().all() if r[0]]

    # Estadisticas rapidas
    total_hoy = db.query(models.AuditLog).filter(
        func.date(models.AuditLog.created_at) == date.today()
    ).count()

    return templates.TemplateResponse("auditoria/lista.html", {
        "request": request,
        "registros": registros,
        "usuarios": usuarios,
        "acciones_disponibles": acciones_disponibles,
        "entidades_disponibles": sorted(entidades_disponibles),
        "buscar": buscar or "",
        "usuario_id": usuario_id or "",
        "accion": accion or "",
        "entidad": entidad or "",
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "total": total,
        "total_hoy": total_hoy,
        "pagina": pag,
        "total_paginas": total_paginas,
    })
