from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.producto import Precio, PrecioOut


class VarianteIn(BaseModel):
    """Fila de la tabla editable de variantes (HU027): nombre, precio propio y stock."""

    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = Field(examples=["Cuarzo rosa"])
    precio: Precio | None = Field(None, examples=["32.00"])  # vacío = hereda el precio_base del producto
    existencias: Annotated[int, Field(ge=0)] = 0
    propiedades: Annotated[str, StringConstraints(strip_whitespace=True)] | None = Field(None, examples=["Amor propio y armonía"])


class VarianteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    nombre: str
    precio: Decimal | None = Field(examples=["32.00"])
    precio_efectivo: PrecioOut
    existencias: int
    propiedades: str | None
