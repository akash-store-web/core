from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.pedido import PedidoBandeja, PedidoDetalle
from app.services import pedidos as servicio

router = APIRouter(prefix="/admin/pedidos", tags=["admin: pedidos"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[PedidoBandeja])
def listar_pedidos(estado: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    """Bandeja de pedidos (HU017), del más reciente al más antiguo. `q` busca por número, nombre o teléfono.
    Estados: pendiente_pago, por_validar, confirmado, rechazado, enviado, entregado, vencido."""
    return servicio.listar_pedidos(db, estado, q)


@router.get("/{pedido_id}", response_model=PedidoDetalle)
def obtener_pedido(pedido_id: int, db: Session = Depends(get_db)):
    return servicio.obtener_pedido(db, pedido_id)
