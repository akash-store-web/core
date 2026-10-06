"""HU009: validar el carrito contra la disponibilidad real."""
from collections import Counter
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models.variante import Variante
from app.schemas.carrito import CarritoIn, CarritoOut, ItemCarritoOut


def unidades_reservadas(db: Session, variante_ids: list[int]) -> dict[int, int]:
    """Unidades apartadas por pedidos pendientes de pago cuya reserva sigue vigente.

    Hoy devuelve {} porque aún no se crean pedidos (HU010/HU011). Cuando existan, este es el
    único lugar que hay que completar: el carrito y el checkout ya restan lo que devuelva."""
    return {}


def disponibles_para_venta(db: Session, variantes: list[Variante]) -> dict[int, int]:
    reservadas = unidades_reservadas(db, [v.id for v in variantes])
    return {v.id: max(v.existencias - reservadas.get(v.id, 0), 0) for v in variantes}


def validar_carrito(db: Session, carrito: CarritoIn) -> CarritoOut:
    # Si la misma variante llega dos veces, se suman las cantidades.
    pedidas = Counter()
    for item in carrito.items:
        pedidas[item.variante_id] += item.cantidad

    variantes = {
        v.id: v
        for v in db.query(Variante)
        .filter(Variante.id.in_(pedidas))
        .options(selectinload(Variante.producto))
        .all()
    }
    disponibles = disponibles_para_venta(db, list(variantes.values()))

    items = []
    for variante_id, cantidad in pedidas.items():
        variante = variantes.get(variante_id)
        if variante is None or not variante.producto.publicado:
            items.append(ItemCarritoOut(
                variante_id=variante_id, producto_id=variante.producto_id if variante else None,
                producto=variante.producto.nombre if variante else None, variante=variante.nombre if variante else None,
                es_pieza_natural=False, cantidad=cantidad, estado="no_disponible", cantidad_maxima=0,
                precio_unitario=None, subtotal=Decimal("0.00"),
                mensaje="Este producto ya no está disponible; quítalo del pedido",
            ))
            continue

        maximo = disponibles[variante_id]
        precio = variante.precio_efectivo
        if maximo == 0:
            estado, mensaje = "agotado", "Agotado; quítalo del pedido"
        elif cantidad > maximo:
            estado, mensaje = "stock_insuficiente", f"Solo quedan {maximo}; ajusta la cantidad"
        else:
            estado, mensaje = "ok", None
        items.append(ItemCarritoOut(
            variante_id=variante_id, producto_id=variante.producto_id, producto=variante.producto.nombre,
            variante=variante.nombre, es_pieza_natural=variante.producto.es_pieza_natural, cantidad=cantidad,
            estado=estado, cantidad_maxima=maximo, precio_unitario=precio,
            subtotal=(precio * min(cantidad, maximo)).quantize(Decimal("0.01")), mensaje=mensaje,
        ))

    total = sum((i.subtotal for i in items), Decimal("0.00"))
    return CarritoOut(valido=all(i.estado == "ok" for i in items), items=items, total=total)
