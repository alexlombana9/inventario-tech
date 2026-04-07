# Patron CRUD Estandar — TechStock

## Modelo (models.py)
```python
class MiEntidad(Base):
    __tablename__ = "mi_entidad"
    __table_args__ = (UniqueConstraint("campo_unico", "local_id", name="uq_mi_entidad_campo_local"),)
    id = Column(Integer, primary_key=True, index=True)
    campo_unico = Column(String(100), nullable=False)
    descripcion = Column(String(500))
    activo = Column(Boolean, default=True)
    local_id = Column(Integer, ForeignKey("locales.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

## Router (routers/mi_modulo.py)
```python
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
from auth import require_permiso, log_audit, set_flash, get_local_id
import models

router = APIRouter(prefix="/mi-modulo", tags=["MiModulo"])

@router.get("")
def lista(request: Request, db: Session = Depends(get_db), user = Depends(require_permiso("mi_modulo"))):
    local_id = get_local_id(request)
    query = db.query(models.MiEntidad).filter(models.MiEntidad.activo == True)
    if local_id is not None:
        query = query.filter(models.MiEntidad.local_id == local_id)
    items = query.order_by(models.MiEntidad.created_at.desc()).all()
    return templates.TemplateResponse("mi_modulo/lista.html", {**base_ctx, "items": items})

@router.get("/nuevo")    # Form crear
@router.post("/nuevo")   # Guardar — entity.local_id = local_id, log_audit, redirect 303
@router.get("/{id}/editar")    # Form editar — filtrar por local_id
@router.post("/{id}/editar")   # Guardar — log_audit, redirect 303
@router.post("/{id}/eliminar") # Soft delete — activo=False, log_audit, redirect 303
@router.get("/{id}/detalle")   # Detalle — filtrar por local_id
```

## Migracion (migrations.py)
```python
def migrate_mi_entidad(conn):
    if not table_exists(conn, "mi_entidad"):
        return  # create_all() ya la creo
    columns = get_table_columns(conn, "mi_entidad")
    if "nuevo_campo" not in columns:
        conn.execute(text("ALTER TABLE mi_entidad ADD COLUMN nuevo_campo VARCHAR(100) DEFAULT ''"))
        conn.commit()
```

## Template (templates/mi_modulo/lista.html)
```html
{% extends "base.html" %}
{% block title %}Mi Modulo{% endblock %}
{% block page_title %}Mi Modulo{% endblock %}
{% block content %}
  <!-- Tabla con datos, botones CRUD -->
  <form method="POST" action="/mi-modulo/{{ item.id }}/eliminar">
    {{ csrf_token(request) }}
    <button type="submit">Eliminar</button>
  </form>
{% endblock %}
{% block scripts %}{% endblock %}
```

## Checklist de Registro
1. Modelo en `models.py` con `activo`, `local_id`, timestamps
2. Migracion idempotente en `migrations.py` (solo PostgreSQL)
3. Router en `routers/mi_modulo.py` con get_local_id + require_permiso + log_audit
4. Templates en `templates/mi_modulo/` (lista, form, detalle)
5. Enlace en sidebar de `templates/base.html`
6. Modulo en `auth.py` → `MODULOS_DISPONIBLES` + `PERMISOS_POR_ROL`
7. `app.include_router(mi_modulo.router)` en `main.py`
8. Tests en `tests/test_mi_modulo.py` con `local_id=sample_local.id`
9. Constantes en `utils/constants.py` si aplica
