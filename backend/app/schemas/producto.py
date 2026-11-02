from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# T-07 (HU014 E7, HU027 E8): de 0.01 a 9,999.99 con 2 decimales.
PRECIO_MAXIMO = Decimal("9999.99")
Precio = Annotated[Decimal, Field(gt=0, le=PRECIO_MAXIMO, max_digits=10, decimal_places=2, examples=["25.00"])]
# Sin ejemplo, Swagger inventa un Decimal aleatorio a partir del patrón y se ve ilegible.
PrecioOut = Annotated[Decimal, Field(examples=["25.00"])]


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    orden: int


class ProductoIn(BaseModel):
    """Datos del formulario de producto (HU014). `publicado` se cambia con su propio endpoint (HU016)."""

    categoria_id: int = Field(examples=[2])
    nombre: Annotated[Texto, StringConstraints(max_length=120)] = Field(examples=["Pulsera de cuarzo"])
    descripcion: Annotated[Texto, StringConstraints(max_length=1000)] = Field(examples=["Pulsera de cuentas de cuarzo natural con hilo elástico."])
    precio_base: Precio
    material: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = Field(None, examples=["Cuarzo natural"])
    medidas: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = Field(None, examples=["Cuentas de 8 mm"])
    peso_g: Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)] | None = Field(None, examples=["12.50"])
    es_pieza_natural: bool = False


class ProductoCrear(ProductoIn):
    """Alta de producto. Nace con la variante "Única" (HU027 #3) y existencias 0: el stock entra solo
    por compras (HU033) o ajustes con motivo (HU034). Si llega `existencias`, se ignora."""


class ProductoEditar(ProductoIn):
    """Edición del producto (HU032). `actualizado_en` es opcional: si llega (el valor que devolvió el GET)
    y otra persona guardó cambios después, responde 409 en lugar de pisarlos (HU032 E10)."""

    actualizado_en: datetime | None = Field(None, examples=["2026-11-01T15:30:00.123456Z"])


class PublicadoIn(BaseModel):
    """HU016: interruptor Activo/Inactivo del listado del panel."""

    publicado: bool = Field(examples=[True])


class ImagenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    orden: int
    es_principal: bool
    es_referencia_escala: bool


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    categoria_id: int
    nombre: str
    descripcion: str
    precio_base: PrecioOut
    material: str | None
    medidas: str | None
    peso_g: Decimal | None = Field(examples=["12.50"])
    es_pieza_natural: bool
    publicado: bool
    creado_en: datetime | None
    actualizado_en: datetime | None  # enviarlo de vuelta en el PUT para detectar ediciones simultáneas
    imagenes: list[ImagenOut] = []


class ProductoListItem(BaseModel):
    """Fila del listado del panel (HU014 #8, Jeremies)."""

    id: int
    nombre: str
    categoria_id: int
    categoria: str
    precio_base: PrecioOut
    publicado: bool
    num_variantes: int  # solo las variantes activas
    existencias_total: int
    agotado: bool
    foto_principal: str  # nunca vacía: si no hay fotos reales, la imagen genérica
    foto_generica: bool  # True = falta subir fotos reales (útil como aviso en el panel)
