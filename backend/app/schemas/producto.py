from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Precio = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2, examples=["25.00"])]
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
    descripcion: Texto = Field(examples=["Pulsera de cuentas de cuarzo natural con hilo elástico."])
    precio_base: Precio
    material: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = Field(None, examples=["Cuarzo natural"])
    medidas: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = Field(None, examples=["Cuentas de 8 mm"])
    peso_g: Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)] | None = Field(None, examples=["12.50"])
    es_pieza_natural: bool = False


class ProductoCrear(ProductoIn):
    """Alta de producto. Todo producto nace con la variante "Única" (HU027 #3): si no tiene piedras
    o aromas, funciona con esa única existencia; si los tiene, se renombra y se agregan las demás."""

    existencias: Annotated[int, Field(ge=0)] = Field(0, examples=[5])


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
    imagenes: list[ImagenOut] = []


class ProductoListItem(BaseModel):
    """Fila del listado del panel (HU014 #8, Jeremies)."""

    id: int
    nombre: str
    categoria_id: int
    categoria: str
    precio_base: PrecioOut
    publicado: bool
    num_variantes: int
    existencias_total: int
    agotado: bool
    foto_principal: str | None
