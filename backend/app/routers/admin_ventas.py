from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.ventas import VentasMesOut
from app.services import ventas as servicio

router = APIRouter(prefix="/admin/ventas", tags=["admin: ventas"], dependencies=[Depends(get_current_admin)])


@router.get("/mes", response_model=VentasMesOut)
def ventas_del_mes(anio: int | None = None, mes: int | None = None, db: Session = Depends(get_db)):
    """Ventas confirmadas del mes (HU019), en hora de Lima. Sin parámetros: el mes actual.
    Incluye el mes anterior para comparar. El envío va aparte de los productos."""
    return servicio.ventas_del_mes(db, anio, mes)
