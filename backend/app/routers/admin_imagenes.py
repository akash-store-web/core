from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.producto import ImagenOut
from app.services import imagenes as servicio

router = APIRouter(
    prefix="/admin/productos/{producto_id}/imagenes",
    tags=["admin: fotos"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=ImagenOut, status_code=status.HTTP_201_CREATED)
async def subir_imagen(producto_id: int, foto: UploadFile = File(...), db: Session = Depends(get_db)):
    """Una foto por petición (JPG, PNG o WEBP, máx. 5 MB). Máximo 5 por producto; la primera es la principal."""
    contenido = await foto.read(servicio.MAX_BYTES + 1)
    return servicio.subir_imagen(db, producto_id, contenido)


@router.patch("/{imagen_id}/principal", response_model=list[ImagenOut])
def marcar_principal(producto_id: int, imagen_id: int, db: Session = Depends(get_db)):
    return servicio.marcar_principal(db, producto_id, imagen_id)


@router.delete("/{imagen_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_imagen(producto_id: int, imagen_id: int, db: Session = Depends(get_db)):
    """Si se borra la principal, la siguiente en orden pasa a ser principal."""
    servicio.eliminar_imagen(db, producto_id, imagen_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
