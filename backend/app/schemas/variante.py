from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.producto import Precio, PrecioOut


class VarianteIn(BaseModel):
    """Fila de la tabla editable de variantes (HU027): nombre, precio propio y stock."""

    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = Field(examples=["Cuarzo rosa"])
    precio: Precio | None = Field(None, examples=["32.00"])  # vacío = hereda el precio_base del producto
    existencias: Annotated[int, Field(ge=0)] = 0
    propiedades: Annotated[str, StringConstraints(strip_whitespace=True)] | None = Field(None, examples=["Amor propio y armonía"])


class ExistenciasIn(BaseModel):
    """HU015: envía `cambio` (botones +/-, p. ej. -1) o `existencias` (cantidad exacta), no ambos."""

    cambio: int | None = Field(None, examples=[-1])
    existencias: Annotated[int, Field(ge=0)] | None = Field(None, examples=[None])

    @model_validator(mode="after")
    def _uno_solo(self):
        if (self.cambio is None) == (self.existencias is None):
            raise ValueError("Envía 'cambio' o 'existencias', uno solo")
        if self.cambio == 0:
            raise ValueError("'cambio' no puede ser 0")
        return self


class StockOut(BaseModel):
    """Respuesta ligera para el ajuste rápido de stock (HU015)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    existencias: int
    agotado: bool


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
