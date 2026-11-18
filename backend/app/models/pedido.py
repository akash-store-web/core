from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class EstadoPedido:
    """Estados del pedido. La columna `estado` es VARCHAR(20) sin restricción en la BD:
    este es el único lugar donde se definen.

    Decisión del PO (10/11/2026): la web es un catálogo y la venta se cierra por WhatsApp.
    El pedido nace «pendiente» y NO aparta ni descuenta stock; el stock baja recién cuando la
    propietaria confirma la venta en el panel (HU018)."""

    PENDIENTE = "pendiente"    # registrado desde la web; se coordina por WhatsApp (HU010)
    CONFIRMADO = "confirmado"  # venta cobrada: se descuenta el stock (HU018)
    CANCELADO = "cancelado"    # la clienta no concretó (HU018)
    ENVIADO = "enviado"        # HU018
    ENTREGADO = "entregado"    # HU018

    TODOS = (PENDIENTE, CONFIRMADO, CANCELADO, ENVIADO, ENTREGADO)


class MetodoPago:
    WHATSAPP = "whatsapp"  # el pago se coordina por el chat (HU010)


class ModalidadEntrega:
    DELIVERY = "delivery"  # a un distrito con zona de envío; cobra el costo de la zona
    RECOJO = "recojo"      # la clienta recoge; sin costo de envío

    TODAS = (DELIVERY, RECOJO)


PREFIJO_NUMERO = "P-"  # P-0001, P-0002… (HU010 escenario 1)


class Pedido(Base):
    __tablename__ = "pedido"

    id = Column(Integer, primary_key=True)
    numero = Column(String(20), nullable=False, unique=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    distrito_id = Column(Integer, ForeignKey("distrito.id"))
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modalidad_entrega = Column(String(20), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    costo_envio = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    total = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(20), nullable=False)
    comprobante_url = Column(String(255))  # sin uso desde la venta por WhatsApp
    estado = Column(String(20), nullable=False)
    reserva_vence = Column(DateTime(timezone=True))  # sin uso: el pedido no reserva stock

    cliente = relationship("Cliente")
    distrito = relationship("Distrito")
    detalles = relationship("DetallePedido", back_populates="pedido", order_by="DetallePedido.id")
    historial = relationship("HistorialEstadoPedido", back_populates="pedido", order_by="HistorialEstadoPedido.fecha")


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"

    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)  # precio histórico al momento de la compra

    pedido = relationship("Pedido", back_populates="detalles")
    variante = relationship("Variante")


class HistorialEstadoPedido(Base):
    __tablename__ = "historial_estado_pedido"

    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))  # NULL = cambio sin usuario (p. ej. la clienta o vencimiento)
    estado = Column(String(20), nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pedido = relationship("Pedido", back_populates="historial")
    usuario = relationship("Usuario")
