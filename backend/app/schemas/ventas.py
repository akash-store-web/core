"""HU019: resumen de ventas del mes en el panel."""
from pydantic import BaseModel, Field

from app.schemas.producto import PrecioOut


class ResumenMes(BaseModel):
    anio: int = Field(examples=[2026])
    mes: int = Field(examples=[10])
    pedidos: int  # pedidos confirmados en el mes (y que no se cancelaron después)
    total_productos: PrecioOut  # suma de subtotales (sin envío)
    total_envio: PrecioOut  # el envío se muestra aparte (E6)
    total: PrecioOut  # total_productos + total_envio


class VentasMesOut(ResumenMes):
    sin_ventas: bool
    mensaje: str | None = Field(examples=["No hubo ventas confirmadas en noviembre de 2026"])
    mes_anterior: ResumenMes
