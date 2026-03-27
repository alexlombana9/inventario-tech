"""Utilidades financieras compartidas entre deudas y facturas."""
from sqlalchemy.orm import Session


def actualizar_estado_pago(entity, monto_pagado_field: str = "monto_pagado"):
    """Recalcula el estado de una entidad con pagos (deuda o factura).

    Compara monto_pagado/monto_cobrado contra monto_total.
    """
    pagado = getattr(entity, monto_pagado_field, 0) or 0
    total = entity.monto_total or 0

    if pagado >= total:
        entity.estado = "PAGADO"
    elif pagado > 0:
        entity.estado = "PARCIAL"
    else:
        entity.estado = "PENDIENTE"


def siguiente_numero(db: Session, model, campo_numero: str, prefijo: str, local_id: int = None) -> str:
    """Genera el proximo numero correlativo para una entidad.

    Uso: siguiente_numero(db, Factura, "numero_factura", "FAC")
         siguiente_numero(db, Venta, "numero_venta", "VTA")
    """
    query = db.query(model)
    if local_id is not None and hasattr(model, "local_id"):
        query = query.filter(model.local_id == local_id)
    ultimo = query.order_by(model.id.desc()).first()
    if not ultimo:
        return f"{prefijo}-0001"
    try:
        valor = getattr(ultimo, campo_numero)
        num = int(valor.split("-")[-1]) + 1
        return f"{prefijo}-{num:04d}"
    except (ValueError, IndexError, AttributeError):
        return f"{prefijo}-{(ultimo.id or 0) + 1:04d}"
