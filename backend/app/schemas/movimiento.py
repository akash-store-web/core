from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator


class AjusteIn(BaseModel):
    """HU034 escenario 4: ajuste con motivo obligatorio. La cantidad lleva signo:
    negativa si se rompió o perdió, positiva si estaba mal contado."""

    cantidad: int = Field(examples=[-1])
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)] = Field(
        examples=["Se rompió al empacar"])

    @field_validator("cantidad")
    @classmethod
    def _distinta_de_cero(cls, valor: int) -> int:
        if valor == 0:
            raise ValueError("La cantidad del ajuste no puede ser 0")
        return valor


class MovimientoOut(BaseModel):
    id: int
    variante_id: int
    variante: str
    fecha: datetime
    tipo: str  # inventario_inicial | compra | venta | ajuste
    cantidad: int  # con signo: + entra, − sale
    saldo: int  # existencias después del movimiento
    motivo: str | None
    compra_id: int | None  # para abrir la compra (HU033)
    pedido_numero: str | None  # para las ventas (HU010/HU018)
    usuario: str | None  # email de quien lo registró; None = sistema
