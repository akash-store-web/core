"""Carrito público (HU009): sin login, la clienta compra como invitada."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.carrito import CarritoIn, CarritoOut
from app.services import carrito as servicio

router = APIRouter(prefix="/carrito", tags=["carrito (público)"])


@router.post("/validar", response_model=CarritoOut)
def validar_carrito(datos: CarritoIn, db: Session = Depends(get_db)):
    """Revisa cada ítem contra el stock real y los precios vigentes. Siempre responde 200 con el
    resultado; `valido: true` significa que se puede pasar al checkout."""
    return servicio.validar_carrito(db, datos)
