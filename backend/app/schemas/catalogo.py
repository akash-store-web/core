"""Respuestas del catálogo público (sin login). No exponen existencias exactas ni datos internos."""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.producto import PrecioOut


class CategoriaPublica(BaseModel):
    id: int
    nombre: str


class ProductoCatalogo(BaseModel):
    """Tarjeta del catálogo (HU001, HU002, HU003)."""

    id: int
    nombre: str
    categoria_id: int
    categoria: str
    precio: PrecioOut  # el menor precio entre sus variantes
    precio_desde: bool  # True si las variantes tienen precios distintos: mostrar "Desde S/ …"
    disponible: bool  # False = "Agotado" (todas sus variantes en 0)
    es_pieza_natural: bool
    foto_principal: str | None


class VariantePublica(BaseModel):
    id: int
    nombre: str
    precio: PrecioOut
    disponible: bool
    propiedades: str | None


class ImagenPublica(BaseModel):
    url: str
    es_principal: bool
    es_referencia_escala: bool


class FichaProducto(ProductoCatalogo):
    """Ficha del producto. Si `tiene_variantes` es False, no mostrar el selector de piedra o aroma."""

    descripcion: str
    material: str | None
    medidas: str | None
    peso_g: Decimal | None = Field(examples=["12.50"])
    tiene_variantes: bool
    variantes: list[VariantePublica]
    imagenes: list[ImagenPublica]
