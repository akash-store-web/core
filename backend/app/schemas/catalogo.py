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
    precio: PrecioOut  # el menor precio entre sus variantes disponibles (si todas están agotadas, entre todas)
    precio_desde: bool  # True si esas variantes tienen precios distintos: mostrar "Desde S/ …"
    disponible: bool  # False = "Agotado" (ninguna variante con unidades libres, descontando reservas)
    es_pieza_natural: bool
    foto_principal: str  # nunca vacía: si no hay fotos reales, la imagen genérica
    foto_generica: bool  # True = aún no tiene fotos reales


class VariantePublica(BaseModel):
    id: int
    nombre: str
    precio: PrecioOut
    disponible: bool
    ultima_unidad: bool  # HU003 Esc.4: queda exactamente 1 unidad libre ("¡Última unidad!"); nunca la cantidad
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
