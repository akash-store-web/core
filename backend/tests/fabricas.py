"""Datos de prueba para pedidos. Las clientas son ficticias: nunca usar datos de clientas reales."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.pedido import DetallePedido, EstadoPedido, HistorialEstadoPedido, Pedido


def crear_pedido(db: Session, numero: str, items: list[tuple[int, int, str]], estado: str = EstadoPedido.PENDIENTE_PAGO,
                 nombre: str = "Clienta de Prueba", telefono: str = "900000001", fecha: datetime | None = None,
                 distrito_id: int | None = None, costo_envio: str = "10.00", comprobante_url: str | None = None) -> Pedido:
    """items: [(variante_id, cantidad, precio_unitario)]."""
    cliente = Cliente(nombre=nombre, telefono=telefono, correo="clienta@ejemplo.com",
                      direccion="Av. Siempre Viva 123", referencia="Frente al parque")
    subtotal = sum(Decimal(precio) * cantidad for _, cantidad, precio in items)
    fecha = fecha or datetime.now(timezone.utc)
    pedido = Pedido(
        numero=numero, cliente=cliente, distrito_id=distrito_id, fecha=fecha, modalidad_entrega="delivery",
        subtotal=subtotal, costo_envio=Decimal(costo_envio), total=subtotal + Decimal(costo_envio),
        metodo_pago="yape", comprobante_url=comprobante_url, estado=estado,
        reserva_vence=fecha + timedelta(hours=24),
    )
    pedido.detalles = [DetallePedido(variante_id=v, cantidad=c, precio_unitario=Decimal(p)) for v, c, p in items]
    pedido.historial = [HistorialEstadoPedido(estado=EstadoPedido.PENDIENTE_PAGO, fecha=fecha)]
    if estado != EstadoPedido.PENDIENTE_PAGO:
        pedido.historial.append(HistorialEstadoPedido(estado=estado, fecha=fecha + timedelta(minutes=10)))
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido
