"""Datos del Catálogo 2025 para el seed (T-01 #3).

Reutiliza el lector y las validaciones de scripts/cargar_catalogo.py (T-01 #1): la hoja se lee
y se revisa con las mismas reglas del backend; si una fila tiene errores, no se carga nada.
La hoja vive en scripts/data/catalogo_akashstore_2025.xlsx (una sola fuente de verdad).
"""
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

from scripts.cargar_catalogo import a_decimal, agrupar, leer_hoja, revisar, texto

HOJA_POR_DEFECTO = Path(__file__).parent / "data" / "catalogo_akashstore_2025.xlsx"
VARIANTE_UNICA = "Única"


def slug(nombre: str) -> str:
    """'Collar de cuarzo ágata' -> 'collar-de-cuarzo-agata' (nombre de la carpeta de fotos)."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def leer_catalogo(ruta: Path = HOJA_POR_DEFECTO) -> list[dict]:
    """Lista de productos con sus variantes, en el orden de la hoja.

    precio_base None => producto pendiente de precio (el seed lo salta).
    precio de variante None => hereda el precio base (HU027).
    existencias de variante: el valor de la columna opcional 'existencias' o None (usa el valor por defecto).
    Lanza ValueError si la hoja tiene errores (los mismos que lista cargar_catalogo).
    """
    _, registros = leer_hoja(str(ruta))
    productos, problemas = [], []
    for nombre, filas in agrupar(registros).items():
        revision = revisar(nombre, filas)
        if revision["estado"] == "ERROR":
            problemas.extend(revision["errores"])
            continue
        primera, ignorados = filas[0], []
        variantes = []
        for fila in filas:
            existencias = texto(fila.get("existencias"))
            variantes.append({
                "nombre": texto(fila.get("variante")) or VARIANTE_UNICA,
                "precio": a_decimal(fila.get("precio_variante"), "precio_variante", nombre, ignorados),
                "propiedades": texto(fila.get("propiedades")) or None,
                "existencias": int(Decimal(existencias)) if existencias else None,
            })
        productos.append({
            "categoria": revision["categoria"],
            "nombre": nombre,
            "descripcion": texto(primera.get("descripcion")),
            "material": texto(primera.get("material")) or None,
            "medidas": texto(primera.get("medidas")) or None,
            "precio_base": revision["precio_base"],
            "es_pieza_natural": texto(primera.get("es_pieza_natural")).lower() in ("sí", "si"),
            "variantes": variantes,
        })
    if problemas:
        raise ValueError("La hoja tiene errores:\n  - " + "\n  - ".join(problemas))
    return productos
