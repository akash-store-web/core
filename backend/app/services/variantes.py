from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.compra import DetalleCompra
from app.models.movimiento_stock import MovimientoStock
from app.models.pedido import DetallePedido
from app.models.variante import Variante
from app.schemas.variante import VarianteEditar, VarianteIn
from app.services.productos import marcar_modificado, obtener_producto

# T-07 (HU027 E10): máximo de variantes activas por producto.
MAX_VARIANTES_ACTIVAS = 30
ULTIMA_ACTIVA = "El producto debe conservar al menos una variante activa"


def obtener_variante(db: Session, producto_id: int, variante_id: int) -> Variante:
    obtener_producto(db, producto_id)
    variante = db.get(Variante, variante_id)
    if variante is None or variante.producto_id != producto_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return variante


def listar_variantes(db: Session, producto_id: int) -> list[Variante]:
    """Todas, activas y retiradas (cada una indica `activa`)."""
    return obtener_producto(db, producto_id).variantes


def _validar_nombre_unico(db: Session, producto_id: int, nombre: str, excluir_id: int | None = None) -> None:
    """T-07 (HU027 E5): el nombre no se repite dentro del producto (sin mayúsculas ni espacios extremos).
    Incluye las retiradas: en ese caso conviene reactivarla en lugar de crear otra."""
    consulta = db.query(Variante).filter(
        Variante.producto_id == producto_id,
        func.lower(func.trim(Variante.nombre)) == nombre.strip().lower(),
    )
    if excluir_id is not None:
        consulta = consulta.filter(Variante.id != excluir_id)
    existente = consulta.first()
    if existente:
        extra = "; está desactivada, reactívala en lugar de crear otra" if not existente.activa else ""
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El producto ya tiene una variante llamada «{existente.nombre}» (id {existente.id}){extra}",
        )


def _validar_limite(producto) -> None:
    if sum(1 for v in producto.variantes if v.activa) >= MAX_VARIANTES_ACTIVAS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Un producto puede tener como máximo {MAX_VARIANTES_ACTIVAS} variantes activas",
        )


def _es_la_ultima_activa(variante: Variante) -> bool:
    return variante.activa and sum(1 for v in variante.producto.variantes if v.activa) == 1


def _tiene_historial(db: Session, variante_id: int) -> bool:
    """Movimientos de stock, compras o pedidos: si existen, la variante no se puede borrar."""
    return any(
        db.query(modelo.id).filter(modelo.variante_id == variante_id).first() is not None
        for modelo in (MovimientoStock, DetalleCompra, DetallePedido)
    )


def _desactivar(db: Session, variante: Variante) -> Variante:
    variante.activa = False
    marcar_modificado(variante.producto)
    db.commit()
    db.refresh(variante)
    return variante


def crear_variante(db: Session, producto_id: int, datos: VarianteIn) -> Variante:
    producto = obtener_producto(db, producto_id)
    _validar_nombre_unico(db, producto_id, datos.nombre)
    _validar_limite(producto)
    variante = Variante(producto_id=producto_id, existencias=0, **datos.model_dump())  # HU034: nace sin stock
    db.add(variante)
    marcar_modificado(producto)
    db.commit()
    db.refresh(variante)
    return variante


def actualizar_variante(db: Session, producto_id: int, variante_id: int, datos: VarianteEditar) -> Variante:
    variante = obtener_variante(db, producto_id, variante_id)
    _validar_nombre_unico(db, producto_id, datos.nombre, excluir_id=variante_id)
    cambios = datos.model_dump(exclude={"activa"})
    if datos.activa is not None and datos.activa != variante.activa:
        if datos.activa:
            _validar_limite(variante.producto)
        elif _es_la_ultima_activa(variante):
            raise HTTPException(status.HTTP_409_CONFLICT, ULTIMA_ACTIVA)
        cambios["activa"] = datos.activa
    for campo, valor in cambios.items():
        setattr(variante, campo, valor)
    marcar_modificado(variante.producto)
    db.commit()
    db.refresh(variante)
    return variante


def eliminar_variante(db: Session, producto_id: int, variante_id: int) -> Variante | None:
    """Sin historial se borra (devuelve None). Con movimientos, compras o pedidos se desactiva
    (devuelve la variante): así no se pierde la trazabilidad del stock (HU027 E9, HU032 E8)."""
    variante = obtener_variante(db, producto_id, variante_id)
    if _es_la_ultima_activa(variante):
        # HU027 #3: todo producto conserva al menos una variante activa, que es donde vive su stock.
        raise HTTPException(status.HTTP_409_CONFLICT, ULTIMA_ACTIVA)
    if _tiene_historial(db, variante_id):
        return _desactivar(db, variante)

    marcar_modificado(variante.producto)
    db.delete(variante)
    try:
        db.commit()
    except IntegrityError:
        # Otra tabla sin ON DELETE (p. ej. un aviso de reingreso) aún apunta a la variante: se desactiva.
        db.rollback()
        return _desactivar(db, obtener_variante(db, producto_id, variante_id))
    return None
