from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class EstadoPedido:
    """Estados del pedido. La columna `estado` es VARCHAR(20) sin restricción en la BD:
    este es el único lugar donde se definen (HU011, HU017, HU018)."""

    PENDIENTE_PAGO = "pendiente_pago"  # creado; stock reservado hasta reserva_vence (HU010)
    POR_VALIDAR = "por_validar"        # la clienta adjuntó el comprobante (HU011)
    CONFIRMADO = "confirmado"          # pago aprobado: se descuenta el stock (HU018)
    RECHAZADO = "rechazado"            # pago rechazado: no se descuenta (HU018)
    ENVIADO = "enviado"                # HU018
    ENTREGADO = "entregado"            # HU018
    VENCIDO = "vencido"                # la reserva venció sin pago

    TODOS = (PENDIENTE_PAGO, POR_VALIDAR, CONFIRMADO, RECHAZADO, ENVIADO, ENTREGADO, VENCIDO)


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
    comprobante_url = Column(String(255))
    estado = Column(String(20), nullable=False)
    reserva_vence = Column(DateTime(timezone=True))

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
