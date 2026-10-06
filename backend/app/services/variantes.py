from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.variante import Variante
from app.schemas.variante import ExistenciasIn, VarianteIn
from app.services.productos import obtener_producto


def obtener_variante(db: Session, producto_id: int, variante_id: int) -> Variante:
    obtener_producto(db, producto_id)
    variante = db.get(Variante, variante_id)
    if variante is None or variante.producto_id != producto_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return variante


def listar_variantes(db: Session, producto_id: int) -> list[Variante]:
    return obtener_producto(db, producto_id).variantes


def crear_variante(db: Session, producto_id: int, datos: VarianteIn) -> Variante:
    obtener_producto(db, producto_id)
    variante = Variante(producto_id=producto_id, **datos.model_dump())
    db.add(variante)
    db.commit()
    db.refresh(variante)
    return variante


def actualizar_variante(db: Session, producto_id: int, variante_id: int, datos: VarianteIn) -> Variante:
    variante = obtener_variante(db, producto_id, variante_id)
    for campo, valor in datos.model_dump().items():
        setattr(variante, campo, valor)
    db.commit()
    db.refresh(variante)
    return variante


def ajustar_existencias(db: Session, variante_id: int, cambio: int) -> bool:
    """Suma `cambio` (positivo o negativo) en una sola sentencia SQL, para que dos ajustes
    simultáneos no se pisen. Devuelve False si el resultado quedaría negativo.
    No hace commit: quien llama decide la transacción (HU015 y, más adelante, propuestas de stock)."""
    resultado = db.execute(
        update(Variante)
        .where(Variante.id == variante_id, Variante.existencias + cambio >= 0)
        .values(existencias=Variante.existencias + cambio)
    )
    return resultado.rowcount == 1


def actualizar_existencias(db: Session, producto_id: int, variante_id: int, datos: ExistenciasIn) -> Variante:
    variante = obtener_variante(db, producto_id, variante_id)
    if datos.existencias is not None:
        variante.existencias = datos.existencias
    elif not ajustar_existencias(db, variante.id, datos.cambio):
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Las existencias no pueden quedar en negativo")
    db.commit()
    db.refresh(variante)
    return variante


def eliminar_variante(db: Session, producto_id: int, variante_id: int) -> None:
    variante = obtener_variante(db, producto_id, variante_id)
    if len(variante.producto.variantes) == 1:
        # HU027 #3: todo producto conserva al menos una variante, que es donde vive su stock.
        raise HTTPException(status.HTTP_409_CONFLICT, "El producto debe conservar al menos una variante")
    db.delete(variante)
    try:
        db.commit()
    except IntegrityError:
        # Las FK no tienen ON DELETE: si la variante ya está en un pedido o en un aviso
        # de reingreso, la base rechaza el borrado. Se deja en 0 existencias en su lugar.
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La variante ya tiene pedidos o avisos asociados; deja sus existencias en 0 en lugar de borrarla",
        )
