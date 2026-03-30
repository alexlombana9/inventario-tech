"""Validacion de archivos subidos por magic bytes.

Verifica que el contenido binario del archivo coincida con los tipos
MIME esperados, previniendo subida de archivos maliciosos disfrazados
con extension falsa.
"""

# Firmas binarias (magic bytes) por tipo de archivo
MAGIC_BYTES = {
    "png": [b"\x89PNG"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "xlsx": [b"PK\x03\x04"],
    "zip": [b"PK\x03\x04"],
    "pdf": [b"%PDF"],
}

# Tipos con validacion especial (offset no contiguo)
_SPECIAL_TYPES = {"webp"}


def _check_webp(content: bytes) -> bool:
    """WEBP usa RIFF container: bytes 0-3 = 'RIFF', bytes 8-11 = 'WEBP'."""
    return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"


def validate_file_content(content: bytes, allowed_types: list[str]) -> bool:
    """Valida que el contenido del archivo coincida con los tipos permitidos.

    Args:
        content: Bytes del archivo subido.
        allowed_types: Lista de extensiones permitidas (sin punto), ej: ["jpg", "png"].

    Returns:
        True si el contenido coincide con alguno de los tipos permitidos.
    """
    if not content:
        return False
    for file_type in allowed_types:
        ft = file_type.lower()
        # Tipos con validacion especial
        if ft == "webp" and _check_webp(content):
            return True
        # Tipos con magic bytes simples
        signatures = MAGIC_BYTES.get(ft, [])
        for sig in signatures:
            if content[:len(sig)] == sig:
                return True
    return False
