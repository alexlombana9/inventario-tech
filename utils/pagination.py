"""Utilidad de paginacion compartida para TechStock."""


def paginate(query, page: int, per_page: int = 20):
    """Pagina una query SQLAlchemy.

    Retorna: (items, total, total_pages)
    """
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return items, total, total_pages
