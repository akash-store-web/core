"""HU034: ajustes con motivo e historial de movimientos (reemplaza el PATCH manual de stock de HU015)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models.usuario import Usuario
from app.schemas.movimiento import AjusteIn, MovimientoOut
from app.services import movimientos as servicio

router = APIRouter(prefix="/admin", tags=["admin: stock"], dependencies=[Depends(get_current_admin)])


@router.post("/variantes/{variante_id}/ajustes", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
def registrar_ajuste(variante_id: int, datos: AjusteIn, usuario: Usuario = Depends(get_current_admin),
                     db: Session = Depends(get_db)):
    """Producto roto, perdido o mal contado: `cantidad` con signo y `motivo` obligatorio.
    409 si las existencias quedarían en negativo."""
    return servicio.registrar_ajuste(db, variante_id, datos.cantidad, datos.motivo, usuario.id)


@router.get("/variantes/{variante_id}/movimientos", response_model=list[MovimientoOut])
def historial_de_variante(variante_id: int, db: Session = Depends(get_db)):
    """Historial de la variante, del más reciente al más antiguo, con el saldo después de cada movimiento."""
    return servicio.historial_de_variante(db, variante_id)


@router.get("/productos/{producto_id}/movimientos", response_model=list[MovimientoOut])
def historial_de_producto(producto_id: int, db: Session = Depends(get_db)):
    """Historial de todas las variantes del producto (cada fila indica su variante)."""
    return servicio.historial_de_producto(db, producto_id)
