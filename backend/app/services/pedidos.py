"""HU010: registrar el pedido que se envía por WhatsApp. HU017: bandeja y detalle del panel.
HU018: cambiar el estado del pedido (confirmar la venta descuenta el stock)."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Integer, cast, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.cliente import Cliente
from app.models.movimiento_stock import TipoMovimiento
from app.models.distrito import Distrito
from app.models.pedido import (PREFIJO_NUMERO, DetallePedido, EstadoPedido, HistorialEstadoPedido, MetodoPago,
                               ModalidadEntrega, Pedido)
from app.models.variante import Variante
from app.schemas.carrito import CarritoIn, ItemCarritoIn
from app.schemas.pedido import (MAX_POR_LINEA, CambioEstadoOut, ClientaOut, ItemPedidoOut, LineaPedidoOut,
                                PedidoBandeja, PedidoCreadoOut, PedidoDetalle, PedidoIn)
from app.services.carrito import validar_carrito
from app.services.envios import costo_envio
from app.services.movimientos import registrar_movimiento

VENTANA_DOBLE_ENVIO = timedelta(minutes=2)  # HU010 E9


def _utc(fecha: datetime) -> datetime:
    """SQLite (pruebas) devuelve fechas sin zona; en Postgres ya vienen con zona."""
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _siguiente_numero(db: Session) -> str:
    ultimo = db.query(func.max(cast(func.substr(Pedido.numero, len(PREFIJO_NUMERO) + 1), Integer))).filter(
        Pedido.numero.like(f"{PREFIJO_NUMERO}%")).scalar()
    return f"{PREFIJO_NUMERO}{(ultimo or 0) + 1:04d}"


def _pedido_repetido(db: Session, celular: str, pedidas: Counter) -> Pedido | None:
    """HU010 E9: el mismo celular con los mismos productos y cantidades hace menos de 2 minutos."""
    limite = datetime.now(timezone.utc) - VENTANA_DOBLE_ENVIO
    recientes = (
        db.query(Pedido).join(Pedido.cliente)
        .filter(Cliente.telefono == celular, Pedido.estado == EstadoPedido.PENDIENTE)
        .options(selectinload(Pedido.detalles))
        .order_by(Pedido.id.desc()).limit(5).all()
    )
    for pedido in recientes:
        if _utc(pedido.fecha) >= limite and Counter({d.variante_id: d.cantidad for d in pedido.detalles}) == pedidas:
            return pedido
    return None


def _creado_out(db: Session, pedido_id: int, repetido: bool = False) -> PedidoCreadoOut:
    pedido = (
        db.query(Pedido).filter(Pedido.id == pedido_id)
        .options(selectinload(Pedido.cliente), selectinload(Pedido.distrito),
                 selectinload(Pedido.detalles).selectinload(DetallePedido.variante).selectinload(Variante.producto))
        .one()
    )
    c = pedido.cliente
    return PedidoCreadoOut(
        numero=pedido.numero, estado=pedido.estado, fecha=pedido.fecha, nombre=c.nombre, celular=c.telefono,
        distrito=pedido.distrito.nombre, modalidad_entrega=pedido.modalidad_entrega,
        direccion=c.direccion, referencia=c.referencia,
        items=[
            LineaPedidoOut(variante_id=d.variante_id, producto=d.variante.producto.nombre, variante=d.variante.nombre,
                           cantidad=d.cantidad, precio_unitario=d.precio_unitario,
                           subtotal=(d.precio_unitario * d.cantidad).quantize(Decimal("0.01")))
            for d in pedido.detalles
        ],
        subtotal=pedido.subtotal, costo_envio=pedido.costo_envio, total=pedido.total, repetido=repetido,
    )


def registrar_pedido(db: Session, datos: PedidoIn) -> PedidoCreadoOut:
    """HU010: registra el pedido «pendiente» que la clienta envía por WhatsApp.

    No descuenta ni aparta stock (se descuenta al confirmar la venta, HU018); sí exige que haya
    unidades al momento de enviarlo (E6). Precios, envío y total los calcula siempre el servidor (E7)."""
    pedidas = Counter()
    for item in datos.items:
        pedidas[item.variante_id] += item.cantidad
    if any(cantidad > MAX_POR_LINEA for cantidad in pedidas.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Máximo {MAX_POR_LINEA} unidades por producto; para más, escríbenos por WhatsApp")

    distrito = db.get(Distrito, datos.distrito_id)
    if distrito is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Elige un distrito de la lista")
    if datos.modalidad_entrega == ModalidadEntrega.DELIVERY:
        envio = costo_envio(distrito)
        if envio is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "El distrito no tiene cobertura de envío; escríbenos por WhatsApp para coordinar")
    else:
        envio = Decimal("0.00")

    # Un pedido nuevo a la vez: el correlativo y el control de doble envío no pueden cruzarse.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('pedido_nuevo'))"))

    repetido = _pedido_repetido(db, datos.celular, pedidas)
    if repetido is not None:
        repetido_id = repetido.id
        db.rollback()  # suelta el candado
        return _creado_out(db, repetido_id, repetido=True)

    revision = validar_carrito(db, CarritoIn(items=[ItemCarritoIn(variante_id=v, cantidad=c)
                                                   for v, c in pedidas.items()]))
    if not revision.valido:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, {
            "mensaje": "Algunos productos ya no están disponibles; quítalos o ajusta la cantidad antes de enviar",
            "items": [
                {"variante_id": i.variante_id, "producto": i.producto, "variante": i.variante, "estado": i.estado,
                 "cantidad_maxima": i.cantidad_maxima, "mensaje": i.mensaje}
                for i in revision.items if i.estado != "ok"
            ],
        })

    ahora = datetime.now(timezone.utc)
    subtotal = sum((i.precio_unitario * i.cantidad for i in revision.items), Decimal("0.00"))
    pedido = Pedido(
        numero=_siguiente_numero(db),
        cliente=Cliente(nombre=datos.nombre, telefono=datos.celular, direccion=datos.direccion,
                        referencia=datos.referencia),
        distrito_id=distrito.id, fecha=ahora, modalidad_entrega=datos.modalidad_entrega,
        subtotal=subtotal, costo_envio=envio, total=subtotal + envio,
        metodo_pago=MetodoPago.WHATSAPP, estado=EstadoPedido.PENDIENTE,
        detalles=[DetallePedido(variante_id=i.variante_id, cantidad=i.cantidad, precio_unitario=i.precio_unitario)
                  for i in revision.items],
        historial=[HistorialEstadoPedido(estado=EstadoPedido.PENDIENTE, fecha=ahora)],
    )
    try:
        db.add(pedido)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo registrar el pedido; inténtalo de nuevo")
    return _creado_out(db, pedido.id)


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
            num_items=sum(d.cantidad for d in p.detalles),
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
        metodo_pago=pedido.metodo_pago,
        historial=[
            CambioEstadoOut(estado=h.estado, fecha=h.fecha, usuario=h.usuario.email if h.usuario else None)
            for h in pedido.historial
        ],
    )


# --- HU018: cambiar el estado del pedido ---

# Transiciones válidas (decisión de Raúl): cancelado y entregado son finales.
TRANSICIONES = {
    EstadoPedido.PENDIENTE: {EstadoPedido.CONFIRMADO, EstadoPedido.CANCELADO},
    EstadoPedido.CONFIRMADO: {EstadoPedido.ENVIADO, EstadoPedido.CANCELADO},
    EstadoPedido.ENVIADO: {EstadoPedido.ENTREGADO},
    EstadoPedido.CANCELADO: set(),
    EstadoPedido.ENTREGADO: set(),
}


def _faltantes(db: Session, pedido: Pedido) -> list[dict]:
    """HU018 E4: líneas cuyo stock actual no alcanza (las líneas de una misma variante se suman)."""
    pedidas = Counter()
    for d in pedido.detalles:
        pedidas[d.variante_id] += d.cantidad
    faltan = []
    for variante_id, solicitada in pedidas.items():
        variante = db.get(Variante, variante_id)
        if variante.existencias < solicitada:
            faltan.append({"variante_id": variante_id, "producto": variante.producto.nombre,
                           "variante": variante.nombre, "solicitada": solicitada,
                           "disponible": max(variante.existencias, 0)})
    return faltan


def cambiar_estado(db: Session, pedido_id: int, nuevo_estado: str, usuario_id: int) -> PedidoDetalle:
    """HU018. Todo en una transacción: si algo falla, no queda nada a medias.

    - Confirmar: descuenta el stock con un movimiento `venta` por línea (409 si no alcanza, E4).
    - Cancelar un confirmado: devuelve el stock con un `ajuste` por línea (decisión de Raúl, HU019 E7).
    - Cancelar un pendiente, enviado y entregado: solo estado e historial."""
    if nuevo_estado not in EstadoPedido.TODOS or nuevo_estado == EstadoPedido.PENDIENTE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Estado no válido")

    # E5: la fila del pedido queda bloqueada hasta el commit; una segunda confirmación simultánea
    # espera y vuelve a leer el estado ya cambiado (en SQLite, pruebas, FOR UPDATE se ignora).
    pedido = (
        db.query(Pedido).filter(Pedido.id == pedido_id)
        .with_for_update().populate_existing()
        .options(selectinload(Pedido.detalles))
        .first()
    )
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    actual, numero = pedido.estado, pedido.numero
    if nuevo_estado == actual:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"El pedido {numero} ya está {actual}")
    if nuevo_estado not in TRANSICIONES.get(actual, set()):
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"No se puede pasar de {actual} a {nuevo_estado} (pedido {numero})")

    try:
        if nuevo_estado == EstadoPedido.CONFIRMADO:
            faltan = _faltantes(db, pedido)
            if faltan:
                raise HTTPException(status.HTTP_409_CONFLICT, {
                    "mensaje": f"No hay stock suficiente para confirmar el pedido {numero}",
                    "items": faltan,
                })
            for d in pedido.detalles:
                registrar_movimiento(db, d.variante_id, -d.cantidad, TipoMovimiento.VENTA,
                                     pedido_id=pedido.id, usuario_id=usuario_id)
        elif nuevo_estado == EstadoPedido.CANCELADO and actual == EstadoPedido.CONFIRMADO:
            for d in pedido.detalles:
                registrar_movimiento(db, d.variante_id, d.cantidad, TipoMovimiento.AJUSTE,
                                     motivo=f"Cancelación del pedido {numero}",
                                     pedido_id=pedido.id, usuario_id=usuario_id)
        pedido.estado = nuevo_estado
        db.add(HistorialEstadoPedido(pedido_id=pedido.id, estado=nuevo_estado, usuario_id=usuario_id,
                                     fecha=datetime.now(timezone.utc)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obtener_pedido(db, pedido_id)
