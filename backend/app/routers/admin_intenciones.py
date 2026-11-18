"""HU008 (AKASH-180): intenciones de cada piedra desde el panel."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.intencion import IntencionBreve, IntencionesIn, IntencionOut
from app.services import intenciones as servicio

router = APIRouter(prefix="/admin", tags=["admin: intenciones"], dependencies=[Depends(get_current_admin)])


@router.get("/intenciones", response_model=list[IntencionOut])
def listar_intenciones(db: Session = Depends(get_db)):
    """Activas e inactivas, por nombre, para el selector del formulario de la piedra."""
    return servicio.listar_intenciones(db)


@router.put("/variantes/{variante_id}/intenciones", response_model=list[IntencionBreve])
def asignar_intenciones(variante_id: int, datos: IntencionesIn, db: Session = Depends(get_db)):
    """Reemplaza las intenciones de la piedra (0 a 5). Las repetidas se guardan una vez.
    422 si son más de 5 distintas o si alguna no existe o está desactivada; 404 si la variante no existe."""
    return servicio.asignar_intenciones(db, variante_id, datos.intencion_ids)
