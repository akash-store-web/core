from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.producto import PrecioOut


class ItemCarritoIn(BaseModel):
    variante_id: int = Field(examples=[1])
    cantidad: Annotated[int, Field(gt=0, le=99)] = Field(examples=[2])


class CarritoIn(BaseModel):
    """El carrito vive en el navegador (HU009); el backend solo valida contra el stock real."""

    items: list[ItemCarritoIn] = Field(min_length=1, max_length=50)


EstadoItem = Literal["ok", "stock_insuficiente", "agotado", "no_disponible"]


class ItemCarritoOut(BaseModel):
    variante_id: int
    producto_id: int | None
    producto: str | None
    variante: str | None
    es_pieza_natural: bool  # repetir el aviso de variación natural al revisar el pedido (HU009 #5)
    cantidad: int  # la solicitada
    estado: EstadoItem
    cantidad_maxima: int  # lo que se puede comprar hoy (0 si agotado o no disponible)
    precio_unitario: PrecioOut | None
    subtotal: Decimal = Field(examples=["50.00"])  # precio × min(cantidad, cantidad_maxima)
    mensaje: str | None  # listo para mostrar si estado != "ok"


class CarritoOut(BaseModel):
    valido: bool  # True = todos los ítems en estado "ok": se puede pasar al checkout
    items: list[ItemCarritoOut]
    total: Decimal = Field(examples=["95.00"])  # suma de subtotales (sin envío)
