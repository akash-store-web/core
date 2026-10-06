"""Endpoints públicos de envío para el checkout: sin login (la clienta compra como invitada)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.envio import CostoEnvioOut, DistritoPublico
from app.services import envios as servicio

router = APIRouter(prefix="/envio", tags=["envío (público)"])


@router.get("/distritos", response_model=list[DistritoPublico])
def listar_distritos(db: Session = Depends(get_db)):
    """Distritos para el selector del checkout, con su costo vigente o sin cobertura.
    No expone la dirección del punto de despacho (domicilio de la propietaria)."""
    return [
        DistritoPublico(id=d.id, nombre=d.nombre, con_cobertura=d.con_cobertura, costo_envio=servicio.costo_envio(d))
        for d in servicio.listar_distritos(db)
    ]


@router.get("/costo", response_model=CostoEnvioOut)
def costo_envio(distrito_id: int, db: Session = Depends(get_db)):
    distrito = servicio.obtener_distrito(db, distrito_id)
    return CostoEnvioOut(
        distrito_id=distrito.id,
        distrito=distrito.nombre,
        con_cobertura=distrito.con_cobertura,
        costo_envio=servicio.costo_envio(distrito),
    )
