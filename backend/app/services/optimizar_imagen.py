"""HU001: reduce el peso de las fotos antes de guardarlas en Storage."""
from io import BytesIO

from PIL import Image, ImageOps

LADO_MAX = 1200
CALIDAD = 82


def optimizar(contenido: bytes, tipo: str) -> tuple[bytes, str]:
    """Achica la foto a LADO_MAX px y la convierte a WEBP. Si algo falla o no mejora, devuelve la original."""
    try:
        with Image.open(BytesIO(contenido)) as original:
            foto = ImageOps.exif_transpose(original)  # respeta la orientación del celular
            foto.thumbnail((LADO_MAX, LADO_MAX))
            if foto.mode not in ("RGB", "RGBA"):
                foto = foto.convert("RGBA" if foto.mode in ("LA", "P", "PA") else "RGB")
            salida = BytesIO()
            foto.save(salida, "WEBP", quality=CALIDAD, method=4)
    except Exception:
        return contenido, tipo
    optimizada = salida.getvalue()
    if len(optimizada) >= len(contenido):
        return contenido, tipo
    return optimizada, "image/webp"