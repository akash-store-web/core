"""HU017: ver los pedidos recibidos (bandeja y detalle del panel)."""
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.cliente import Cliente
from app.models.pedido import DetallePedido, EstadoPedido, HistorialEstadoPedido, Pedido
from app.models.variante import Variante
from app.schemas.pedido import CambioEstadoOut, ClientaOut, ItemPedidoOut, PedidoBandeja, PedidoDetalle


def listar_pedidos(db: Session, estado: str | None = None, q: str | None = None) -> list[PedidoBandeja]:
    if estado is not None and estado not in EstadoPedido.TODOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Estado no válido; usa uno de: {', '.join(EstadoPedido.TODOS)}")
    consulta = (
        db.query(Pedido)
        .join(Pedido.cliente)
        .options(selectinload(Pedido.cliente), selectinload(Pedido.detalles))
        .order_by(Pedido.fecha.desc(), Pedido.id.desc())  # lo más reciente primero
    )
    if estado:
        consulta = consulta.filter(Pedido.estado == estado)
    if q and q.strip():
        patron = f"%{q.strip()}%"
        consulta = consulta.filter(or_(Pedido.numero.ilike(patron), Cliente.nombre.ilike(patron),
                                       Cliente.telefono.ilike(patron)))
    return [
        PedidoBandeja(
            id=p.id, numero=p.numero, fecha=p.fecha, clienta=p.cliente.nombre, telefono=p.cliente.telefono,
            total=p.total, metodo_pago=p.metodo_pago, estado=p.estado,
            num_items=sum(d.cantidad for d in p.detalles), tiene_comprobante=bool(p.comprobante_url),
            reserva_vence=p.reserva_vence,
        )
        for p in consulta.all()
    ]


def obtener_pedido(db: Session, pedido_id: int) -> PedidoDetalle:
    pedido = (
        db.query(Pedido)
        .filter(Pedido.id == pedido_id)
        .options(
            selectinload(Pedido.cliente),
            selectinload(Pedido.distrito),
            selectinload(Pedido.detalles).selectinload(DetallePedido.variante).selectinload(Variante.producto),
            selectinload(Pedido.historial).selectinload(HistorialEstadoPedido.usuario),
        )
        .first()
    )
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    c = pedido.cliente
    return PedidoDetalle(
        id=pedido.id, numero=pedido.numero, fecha=pedido.fecha, estado=pedido.estado,
        clienta=ClientaOut(nombre=c.nombre, telefono=c.telefono, correo=c.correo, direccion=c.direccion,
                           referencia=c.referencia),
        distrito=pedido.distrito.nombre if pedido.distrito else None,
        modalidad_entrega=pedido.modalidad_entrega,
        items=[
            ItemPedidoOut(
                variante_id=d.variante_id, producto_id=d.variante.producto_id, producto=d.variante.producto.nombre,
                variante=d.variante.nombre, cantidad=d.cantidad, precio_unitario=d.precio_unitario,
                subtotal=d.precio_unitario * d.cantidad,
            )
            for d in pedido.detalles
        ],
        subtotal=pedido.subtotal, costo_envio=pedido.costo_envio, total=pedido.total,
        metodo_pago=pedido.metodo_pago, comprobante_url=pedido.comprobante_url, reserva_vence=pedido.reserva_vence,
        historial=[
            CambioEstadoOut(estado=h.estado, fecha=h.fecha, usuario=h.usuario.email if h.usuario else None)
            for h in pedido.historial
        ],
    )
