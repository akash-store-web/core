from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.producto import PrecioOut


class PedidoBandeja(BaseModel):
    """Fila de la bandeja de pedidos del panel (HU017)."""

    id: int
    numero: str
    fecha: datetime
    clienta: str
    telefono: str
    total: PrecioOut
    metodo_pago: str
    estado: str
    num_items: int  # unidades totales del pedido
    tiene_comprobante: bool
    reserva_vence: datetime | None


class ClientaOut(BaseModel):
    nombre: str
    telefono: str
    correo: str
    direccion: str
    referencia: str | None


class ItemPedidoOut(BaseModel):
    variante_id: int
    producto_id: int
    producto: str
    variante: str
    cantidad: int
    precio_unitario: PrecioOut  # precio histórico: el que pagó la clienta, aunque luego cambie
    subtotal: Decimal = Field(examples=["90.00"])


class CambioEstadoOut(BaseModel):
    estado: str
    fecha: datetime
    usuario: str | None  # email de quien lo cambió; None = la clienta o el sistema


class PedidoDetalle(BaseModel):
    id: int
    numero: str
    fecha: datetime
    estado: str
    clienta: ClientaOut
    distrito: str | None
    modalidad_entrega: str
    items: list[ItemPedidoOut]
    subtotal: PrecioOut
    costo_envio: PrecioOut
    total: PrecioOut
    metodo_pago: str
    comprobante_url: str | None
    reserva_vence: datetime | None
    historial: list[CambioEstadoOut]
