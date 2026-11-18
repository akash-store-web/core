"""Datos de prueba para pedidos. Las clientas son ficticias: nunca usar datos de clientas reales."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.pedido import DetallePedido, EstadoPedido, HistorialEstadoPedido, MetodoPago, Pedido


def crear_pedido(db: Session, numero: str, items: list[tuple[int, int, str]], estado: str = EstadoPedido.PENDIENTE,
                 nombre: str = "Clienta de Prueba", telefono: str = "900000001", fecha: datetime | None = None,
                 distrito_id: int | None = None, costo_envio: str = "10.00",
                 confirmado_en: datetime | None = None) -> Pedido:
    """items: [(variante_id, cantidad, precio_unitario)]. No mueve stock: es un pedido «histórico».

    El historial sigue el camino real (HU018): enviado y entregado pasan antes por confirmado, cada paso
    10 minutos después del anterior. `confirmado_en` fija la fecha de confirmación (HU019: la venta cuenta
    en el mes en que se confirmó)."""
    cliente = Cliente(nombre=nombre, telefono=telefono, correo="clienta@ejemplo.com",
                      direccion="Av. Siempre Viva 123", referencia="Frente al parque")
    subtotal = sum(Decimal(precio) * cantidad for _, cantidad, precio in items)
    fecha = fecha or datetime.now(timezone.utc)
    pedido = Pedido(
        numero=numero, cliente=cliente, distrito_id=distrito_id, fecha=fecha, modalidad_entrega="delivery",
        subtotal=subtotal, costo_envio=Decimal(costo_envio), total=subtotal + Decimal(costo_envio),
        metodo_pago=MetodoPago.WHATSAPP, estado=estado,
    )
    pedido.detalles = [DetallePedido(variante_id=v, cantidad=c, precio_unitario=Decimal(p)) for v, c, p in items]
    pedido.historial = [HistorialEstadoPedido(estado=EstadoPedido.PENDIENTE, fecha=fecha)]
    caminos = {
        EstadoPedido.PENDIENTE: [],
        EstadoPedido.CONFIRMADO: [EstadoPedido.CONFIRMADO],
        EstadoPedido.CANCELADO: [EstadoPedido.CANCELADO],
        EstadoPedido.ENVIADO: [EstadoPedido.CONFIRMADO, EstadoPedido.ENVIADO],
        EstadoPedido.ENTREGADO: [EstadoPedido.CONFIRMADO, EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO],
    }
    paso = fecha
    for siguiente in caminos[estado]:
        if siguiente == EstadoPedido.CONFIRMADO and confirmado_en is not None:
            paso = confirmado_en
        else:
            paso = paso + timedelta(minutes=10)
        pedido.historial.append(HistorialEstadoPedido(estado=siguiente, fecha=paso))
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


def crear_intenciones(engine, nombres: list[str], inactivas: tuple[str, ...] = ()) -> dict[str, int]:
    """HU008: en Supabase las intenciones las carga el SQL de Diego; en las pruebas se crean aquí.
    Devuelve {nombre: id}."""
    from app.models.intencion import Intencion

    with Session(engine) as db:
        filas = [Intencion(nombre=n, activa=n not in inactivas) for n in nombres]
        db.add_all(filas)
        db.commit()
        return {f.nombre: f.id for f in filas}


def dar_stock(client, auth, variante_id: int, cantidad: int, motivo: str = "Stock de prueba") -> dict:
    """HU034: en las pruebas el stock entra (o sale) con un ajuste con motivo, nunca a mano."""
    respuesta = client.post(f"/admin/variantes/{variante_id}/ajustes",
                            json={"cantidad": cantidad, "motivo": motivo}, headers=auth)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()
