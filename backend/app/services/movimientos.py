"""HU034: el stock solo cambia mediante movimientos registrados.

`registrar_movimiento` es el ÚNICO punto del código que modifica `variante.existencias`.
Lo usan los ajustes (aquí), las compras (HU033) y, más adelante, las ventas (HU010/HU018).
No hace commit: quien llama decide la transacción (una compra con varias líneas es todo o nada).
"""
from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session, selectinload

from app.models.movimiento_stock import MovimientoStock, TipoMovimiento
from app.models.pedido import Pedido
from app.models.variante import Variante
from app.schemas.movimiento import MovimientoOut
from app.services.productos import obtener_producto


def obtener_variante(db: Session, variante_id: int) -> Variante:
    variante = db.get(Variante, variante_id)
    if variante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return variante


def registrar_movimiento(db: Session, variante_id: int, cantidad: int, tipo: str, *, motivo: str | None = None,
                         compra_id: int | None = None, pedido_id: int | None = None,
                         usuario_id: int | None = None) -> MovimientoStock:
    if tipo not in TipoMovimiento.TODOS:
        raise ValueError(f"Tipo de movimiento no válido: {tipo}")
    if cantidad == 0:
        raise ValueError("La cantidad de un movimiento no puede ser 0")
    if tipo == TipoMovimiento.AJUSTE and not (motivo and motivo.strip()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El ajuste necesita un motivo")

    # Una sola sentencia: suma y verifica que no quede negativo, sin carreras entre dos ajustes simultáneos.
    resultado = db.execute(
        update(Variante)
        .where(Variante.id == variante_id, Variante.existencias + cantidad >= 0)
        .values(existencias=Variante.existencias + cantidad)
        .returning(Variante.existencias)
    )
    saldo = resultado.scalar_one_or_none()
    if saldo is None:
        obtener_variante(db, variante_id)  # 404 si no existe
        raise HTTPException(status.HTTP_409_CONFLICT, "Las existencias no pueden quedar en negativo")

    movimiento = MovimientoStock(variante_id=variante_id, tipo=tipo, cantidad=cantidad, saldo=saldo,
                                 motivo=motivo.strip() if motivo else None, compra_id=compra_id,
                                 pedido_id=pedido_id, usuario_id=usuario_id)
    db.add(movimiento)
    db.flush()
    return movimiento


def registrar_ajuste(db: Session, variante_id: int, cantidad: int, motivo: str, usuario_id: int) -> MovimientoOut:
    """HU034 escenario 4: producto roto, perdido o mal contado. La cantidad lleva signo."""
    movimiento = registrar_movimiento(db, variante_id, cantidad, TipoMovimiento.AJUSTE,
                                      motivo=motivo, usuario_id=usuario_id)
    db.commit()
    return historial(db, variante_ids=[movimiento.variante_id], movimiento_id=movimiento.id)[0]


def historial(db: Session, *, variante_ids: list[int], movimiento_id: int | None = None) -> list[MovimientoOut]:
    """Movimientos con fecha, tipo, cantidad y saldo, del más reciente al más antiguo (HU034 escenario 5)."""
    consulta = (
        db.query(MovimientoStock)
        .filter(MovimientoStock.variante_id.in_(variante_ids))
        .options(selectinload(MovimientoStock.variante), selectinload(MovimientoStock.usuario),
                 selectinload(MovimientoStock.pedido))
        .order_by(MovimientoStock.fecha.desc(), MovimientoStock.id.desc())
    )
    if movimiento_id is not None:
        consulta = consulta.filter(MovimientoStock.id == movimiento_id)
    return [_salida(m) for m in consulta.all()]


def historial_de_variante(db: Session, variante_id: int) -> list[MovimientoOut]:
    obtener_variante(db, variante_id)
    return historial(db, variante_ids=[variante_id])


def historial_de_producto(db: Session, producto_id: int) -> list[MovimientoOut]:
    producto = obtener_producto(db, producto_id)
    return historial(db, variante_ids=[v.id for v in producto.variantes])


def _salida(m: MovimientoStock) -> MovimientoOut:
    pedido: Pedido | None = m.pedido
    return MovimientoOut(
        id=m.id, variante_id=m.variante_id, variante=m.variante.nombre, fecha=m.fecha, tipo=m.tipo,
        cantidad=m.cantidad, saldo=m.saldo, motivo=m.motivo, compra_id=m.compra_id,
        pedido_numero=pedido.numero if pedido else None,
        usuario=m.usuario.email if m.usuario else None,
    )
