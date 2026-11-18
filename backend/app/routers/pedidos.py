"""Pedido público (HU010): la clienta, sin cuenta, registra su pedido y lo envía por WhatsApp."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.pedido import PedidoCreadoOut, PedidoIn
from app.services import pedidos as servicio

router = APIRouter(prefix="/pedidos", tags=["pedido (público)"])


@router.post("", response_model=PedidoCreadoOut, status_code=status.HTTP_201_CREATED)
def registrar_pedido(datos: PedidoIn, response: Response, db: Session = Depends(get_db)):
    """Registra el pedido en estado «pendiente» con su número (P-0001…). No descuenta stock: eso pasa
    cuando la propietaria confirma la venta (HU018). Precios, envío y total los calcula el servidor.

    - `201`: pedido nuevo. `200` con `repetido: true`: el mismo pedido llegó dos veces (doble clic).
    - `409`: algún producto se agotó, se despublicó o no alcanza; `detail.items` dice cuáles.
    - `422`: datos inválidos (nombre, celular, distrito sin cobertura, más de 10 por producto)."""
    pedido = servicio.registrar_pedido(db, datos)
    if pedido.repetido:
        response.status_code = status.HTTP_200_OK
    return pedido
