from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.producto import Precio, PrecioOut


class VarianteIn(BaseModel):
    """Nueva variante (HU027): nombre, precio propio y propiedades. Nace con existencias 0:
    el stock entra solo por compras (HU033) o ajustes con motivo (HU034)."""

    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = Field(examples=["Cuarzo rosa"])
    precio: Precio | None = Field(None, examples=["32.00"])  # vacío = hereda el precio_base del producto
    propiedades: Annotated[str, StringConstraints(strip_whitespace=True)] | None = Field(None, examples=["Amor propio y armonía"])


class VarianteEditar(BaseModel):
    """Edición de una variante (HU032): nombre, precio propio y propiedades.
    Las existencias NO se editan aquí (HU032 escenario 4): si llegan, se ignoran."""

    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = Field(examples=["Cuarzo rosa"])
    precio: Precio | None = Field(None, examples=["32.00"])  # vacío = hereda el precio_base del producto
    propiedades: Annotated[str, StringConstraints(strip_whitespace=True)] | None = Field(None, examples=["Amor propio y armonía"])
    # Opcional: true reactiva una variante retirada; false la retira sin borrar su historial. Si no llega, no cambia.
    activa: bool | None = Field(None, examples=[True])


class VarianteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    nombre: str
    precio: Decimal | None = Field(examples=["32.00"])
    precio_efectivo: PrecioOut
    existencias: int
    agotado: bool
    propiedades: str | None
    activa: bool  # False = retirada: no se vende ni se compra, pero conserva su historial


class VarianteEliminada(BaseModel):
    """DELETE de una variante con historial: no se borra, se desactiva (HU027 E9, HU032 E8)."""

    desactivada: bool = Field(examples=[True])
    variante: VarianteOut
    detail: str
