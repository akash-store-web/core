from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.producto import PRECIO_MAXIMO, PrecioOut


MAX_POR_LINEA = 10  # HU009 E6: para más unidades, la clienta escribe por WhatsApp


class ItemCarritoIn(BaseModel):
    variante_id: int = Field(examples=[1])
    cantidad: Annotated[int, Field(gt=0, le=MAX_POR_LINEA)] = Field(examples=[2])
    # HU009 E9: el precio que la clienta vio al agregarlo (guardado en el navegador). Solo sirve para avisar
    # si cambió; nunca se usa para calcular (E10).
    precio_visto: Annotated[Decimal, Field(ge=0, le=PRECIO_MAXIMO, max_digits=10, decimal_places=2)] | None = Field(
        None, examples=["45.00"])


class CarritoIn(BaseModel):
    """El carrito vive en el navegador (HU009); el backend solo valida contra el stock real."""

    items: list[ItemCarritoIn] = Field(min_length=1, max_length=50)


EstadoItem = Literal["ok", "stock_insuficiente", "agotado", "no_disponible", "limite"]


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
    mensaje: str | None  # listo para mostrar si estado != "ok" (o si cambió el precio)
    # HU009 E9: solo si llegó `precio_visto` y difiere del vigente. No bloquea: el estado sigue "ok" si hay stock.
    precio_anterior: PrecioOut | None = None
    precio_cambio: bool = False


class AvisoPiezaNatural(BaseModel):
    """HU006: el aviso se muestra una sola vez en el resumen, con los productos a los que aplica."""

    texto: str
    productos: list[str] = Field(examples=[["Pulsera de cuarzo", "Anillo de plata 925 con piedra"]])


class CarritoOut(BaseModel):
    valido: bool  # True = todos los ítems en estado "ok": se puede pasar al checkout
    items: list[ItemCarritoOut]
    total: Decimal = Field(examples=["95.00"])  # suma de subtotales (sin envío)
    aviso_pieza_natural: AvisoPiezaNatural | None = None  # null si ningún producto es pieza natural
