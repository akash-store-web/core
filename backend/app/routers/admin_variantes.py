from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.variante import ExistenciasIn, StockOut, VarianteIn, VarianteOut
from app.services import variantes as servicio

router = APIRouter(
    prefix="/admin/productos/{producto_id}/variantes",
    tags=["admin: variantes"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=list[VarianteOut])
def listar_variantes(producto_id: int, db: Session = Depends(get_db)):
    return servicio.listar_variantes(db, producto_id)


@router.post("", response_model=VarianteOut, status_code=status.HTTP_201_CREATED)
def crear_variante(producto_id: int, datos: VarianteIn, db: Session = Depends(get_db)):
    return servicio.crear_variante(db, producto_id, datos)


@router.put("/{variante_id}", response_model=VarianteOut)
def actualizar_variante(producto_id: int, variante_id: int, datos: VarianteIn, db: Session = Depends(get_db)):
    return servicio.actualizar_variante(db, producto_id, variante_id, datos)


@router.delete("/{variante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_variante(producto_id: int, variante_id: int, db: Session = Depends(get_db)):
    servicio.eliminar_variante(db, producto_id, variante_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# HU015: ruta corta, porque el listado del panel ya conoce el id de cada variante.
stock_router = APIRouter(prefix="/admin/variantes", tags=["admin: variantes"], dependencies=[Depends(get_current_admin)])


@stock_router.patch("/{variante_id}/stock", response_model=StockOut)
def actualizar_stock(variante_id: int, datos: ExistenciasIn, db: Session = Depends(get_db)):
    """Ajuste rápido desde el listado: {"cambio": -1} para los botones +/- o {"existencias": n}."""
    return servicio.actualizar_existencias(db, variante_id, datos)
