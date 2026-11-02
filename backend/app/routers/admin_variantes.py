from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.variante import VarianteEditar, VarianteEliminada, VarianteIn, VarianteOut
from app.services import variantes as servicio

router = APIRouter(
    prefix="/admin/productos/{producto_id}/variantes",
    tags=["admin: variantes"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=list[VarianteOut])
def listar_variantes(producto_id: int, db: Session = Depends(get_db)):
    """Todas las variantes, activas y retiradas (`activa`)."""
    return servicio.listar_variantes(db, producto_id)


@router.post("", response_model=VarianteOut, status_code=status.HTTP_201_CREATED)
def crear_variante(producto_id: int, datos: VarianteIn, db: Session = Depends(get_db)):
    """409 si el nombre ya existe en el producto; 422 si ya tiene 30 variantes activas."""
    return servicio.crear_variante(db, producto_id, datos)


@router.put("/{variante_id}", response_model=VarianteOut)
def actualizar_variante(producto_id: int, variante_id: int, datos: VarianteEditar, db: Session = Depends(get_db)):
    """HU032: cambia nombre, precio propio, propiedades y (opcional) `activa`. Las existencias no se editan aquí.
    409 si el nombre ya existe en el producto o si se desactiva la última activa; 422 si al reactivar
    se superan 30 variantes activas."""
    return servicio.actualizar_variante(db, producto_id, variante_id, datos)


@router.delete(
    "/{variante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={200: {"model": VarianteEliminada, "description": "Tenía historial: se desactivó en lugar de borrarse"}},
)
def eliminar_variante(producto_id: int, variante_id: int, db: Session = Depends(get_db)):
    """Sin historial: se borra (204). Con movimientos, compras o pedidos: se desactiva y responde 200
    con `{"desactivada": true, ...}`. 409 si es la última variante activa del producto."""
    variante = servicio.eliminar_variante(db, producto_id, variante_id)
    if variante is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    salida = VarianteEliminada(
        desactivada=True, variante=VarianteOut.model_validate(variante),
        detail="La variante tiene historial (stock, compras o pedidos): se desactivó en lugar de borrarse",
    )
    return JSONResponse(salida.model_dump(mode="json"), status_code=status.HTTP_200_OK)
