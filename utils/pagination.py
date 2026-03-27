"""Utilidad de paginacion compartida para TechStock."""


def paginate(query, page: int, per_page: int = 20):
    """Pagina una query SQLAlchemy.

    Retorna: (items, total, total_pages)
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page
    return items, total, total_pages
