"""HU009: validar el carrito contra la disponibilidad real."""
from collections import Counter
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models.variante import Variante
from app.schemas.carrito import MAX_POR_LINEA, AvisoPiezaNatural, CarritoIn, CarritoOut, ItemCarritoOut
from app.services.productos import aviso_pieza_natural

MENSAJE_LIMITE = f"Máximo {MAX_POR_LINEA} unidades por producto; para más, escríbenos por WhatsApp"


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
    vistos: dict[int, Decimal] = {}  # HU009 E9: el primer precio_visto que llegue por variante
    for item in carrito.items:
        pedidas[item.variante_id] += item.cantidad
        if item.precio_visto is not None:
            vistos.setdefault(item.variante_id, item.precio_visto)

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
        if variante is None or not variante.producto.publicado or not variante.activa:
            # HU028 E8: una variante retirada (activa=false) ya no se vende aunque el producto siga publicado.
            mensaje = ("Esta variante ya no está disponible; quítala del pedido"
                       if variante is not None and variante.producto.publicado
                       else "Este producto ya no está disponible; quítalo del pedido")
            items.append(ItemCarritoOut(
                variante_id=variante_id, producto_id=variante.producto_id if variante else None,
                producto=variante.producto.nombre if variante else None, variante=variante.nombre if variante else None,
                es_pieza_natural=False, cantidad=cantidad, estado="no_disponible", cantidad_maxima=0,
                precio_unitario=None, subtotal=Decimal("0.00"), mensaje=mensaje,
            ))
            continue

        maximo = disponibles[variante_id]
        precio = variante.precio_efectivo
        visto = vistos.get(variante_id)
        precio_cambio = visto is not None and visto != precio
        if maximo == 0:
            estado, mensaje = "agotado", "Agotado; quítalo del pedido"
        elif cantidad > MAX_POR_LINEA:
            # HU009 E6: la misma variante en varias líneas suma más de 10 (cada línea ya viene limitada a 10).
            maximo = min(MAX_POR_LINEA, maximo)
            estado, mensaje = "limite", MENSAJE_LIMITE
        elif cantidad > maximo:
            estado, mensaje = "stock_insuficiente", f"Solo quedan {maximo}; ajusta la cantidad"
        else:
            estado, mensaje = "ok", None
        if precio_cambio and mensaje is None:
            mensaje = f"El precio cambió de S/ {visto:.2f} a S/ {precio:.2f}"
        items.append(ItemCarritoOut(
            variante_id=variante_id, producto_id=variante.producto_id, producto=variante.producto.nombre,
            variante=variante.nombre, es_pieza_natural=variante.producto.es_pieza_natural, cantidad=cantidad,
            estado=estado, cantidad_maxima=maximo, precio_unitario=precio,
            subtotal=(precio * min(cantidad, maximo)).quantize(Decimal("0.01")), mensaje=mensaje,
            precio_anterior=visto.quantize(Decimal("0.01")) if precio_cambio else None, precio_cambio=precio_cambio,
        ))

    total = sum((i.subtotal for i in items), Decimal("0.00"))
    # HU006 Esc.2 / E6: un solo aviso aunque haya varias piezas naturales, con los productos sin repetir.
    naturales = list(dict.fromkeys(i.producto for i in items if i.es_pieza_natural))
    aviso = AvisoPiezaNatural(texto=aviso_pieza_natural(), productos=naturales) if naturales else None
    return CarritoOut(valido=all(i.estado == "ok" for i in items), items=items, total=total,
                      aviso_pieza_natural=aviso)
