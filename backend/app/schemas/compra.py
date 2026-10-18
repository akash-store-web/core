from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.schemas.producto import PrecioOut

Costo = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class LineaCompraIn(BaseModel):
    variante_id: int = Field(examples=[1])
    cantidad: Annotated[int, Field(gt=0, le=10000)] = Field(examples=[10])
    costo_unitario: Costo = Field(examples=["18.50"])  # lo que costó cada unidad, según el comprobante


class CompraIn(BaseModel):
    """HU033: compra de mercadería con su boleta o factura. Al guardarse suma el stock de cada variante."""

    proveedor: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)] = Field(
        examples=["Minerales del Sur"])
    proveedor_ruc: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{11}$")] | None = Field(
        None, examples=["20512345678"])
    tipo_comprobante: Literal["boleta", "factura"] = Field(examples=["factura"])
    numero_comprobante: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1,
                                                         max_length=30)] = Field(examples=["F001-000123"])
    fecha: date = Field(examples=["2026-10-15"])
    items: list[LineaCompraIn] = Field(min_length=1, max_length=100)

    @field_validator("fecha")
    @classmethod
    def _no_futura(cls, valor: date) -> date:
        if valor > date.today():
            raise ValueError("La fecha del comprobante no puede ser futura")
        return valor

    @model_validator(mode="after")
    def _sin_variantes_repetidas(self):
        ids = [i.variante_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada variante va una sola vez en la compra; suma sus cantidades en una línea")
        return self


class LineaCompraOut(BaseModel):
    variante_id: int
    producto_id: int
    producto: str
    variante: str
    cantidad: int
    costo_unitario: PrecioOut
    subtotal: Decimal = Field(examples=["185.00"])


class CompraResumen(BaseModel):
    """Fila del listado de compras."""

    id: int
    fecha: date
    proveedor: str
    tipo_comprobante: str
    numero_comprobante: str
    total: PrecioOut
    unidades: int
    tiene_comprobante: bool  # archivo adjunto (AKASH-115)


class CompraOut(CompraResumen):
    proveedor_ruc: str | None
    comprobante_url: str | None
    usuario: str | None
    creado_en: datetime
    items: list[LineaCompraOut]


class IngresoPorCompra(BaseModel):
    """HU033 escenario 4: con qué compras ingresó el stock de un producto."""

    compra_id: int
    fecha: date
    proveedor: str
    tipo_comprobante: str
    numero_comprobante: str
    variante_id: int
    variante: str
    cantidad: int
    costo_unitario: PrecioOut
