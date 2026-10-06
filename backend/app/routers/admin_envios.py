from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.envio import AsignarDistritosIn, DistritoIn, DistritoOut, ZonaEnvioIn, ZonaEnvioOut
from app.services import envios as servicio

router = APIRouter(prefix="/admin", tags=["admin: envíos"], dependencies=[Depends(get_current_admin)])


@router.get("/zonas-envio", response_model=list[ZonaEnvioOut])
def listar_zonas(db: Session = Depends(get_db)):
    return servicio.listar_zonas(db)


@router.post("/zonas-envio", response_model=ZonaEnvioOut, status_code=status.HTTP_201_CREATED)
def crear_zona(datos: ZonaEnvioIn, db: Session = Depends(get_db)):
    return servicio.crear_zona(db, datos)


@router.put("/zonas-envio/{zona_id}", response_model=ZonaEnvioOut)
def actualizar_zona(zona_id: int, datos: ZonaEnvioIn, db: Session = Depends(get_db)):
    """Para dejar de atender una zona sin perder su configuración, enviar activa=false."""
    return servicio.actualizar_zona(db, zona_id, datos)


@router.put("/zonas-envio/{zona_id}/distritos", response_model=ZonaEnvioOut)
def asignar_distritos(zona_id: int, datos: AsignarDistritosIn, db: Session = Depends(get_db)):
    return servicio.asignar_distritos(db, zona_id, datos)


@router.get("/distritos", response_model=list[DistritoOut])
def listar_distritos(zona_envio_id: int | None = None, sin_zona: bool = False, db: Session = Depends(get_db)):
    return servicio.listar_distritos(db, zona_envio_id, sin_zona)


@router.post("/distritos", response_model=DistritoOut, status_code=status.HTTP_201_CREATED)
def crear_distrito(datos: DistritoIn, db: Session = Depends(get_db)):
    return servicio.crear_distrito(db, datos)


@router.put("/distritos/{distrito_id}", response_model=DistritoOut)
def actualizar_distrito(distrito_id: int, datos: DistritoIn, db: Session = Depends(get_db)):
    """Enviar zona_envio_id=null deja el distrito sin cobertura."""
    return servicio.actualizar_distrito(db, distrito_id, datos)
