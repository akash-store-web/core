from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class TipoMovimiento:
    """HU034: el stock solo cambia por uno de estos movimientos."""

    INVENTARIO_INICIAL = "inventario_inicial"  # stock que ya existía antes de HU034 (una sola vez)
    COMPRA = "compra"                          # HU033: ingreso con comprobante
    VENTA = "venta"                            # HU010/HU018: salida al confirmarse un pedido
    AJUSTE = "ajuste"                          # roto, perdido o mal contado; motivo obligatorio

    TODOS = (INVENTARIO_INICIAL, COMPRA, VENTA, AJUSTE)


class MovimientoStock(Base):
    """Historial de existencias por variante (docs/sql/2026-10_sprint2_compras_y_movimientos.sql)."""

    __tablename__ = "movimiento_stock"

    id = Column(Integer, primary_key=True)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    cantidad = Column(Integer, nullable=False)  # con signo: + entra, − sale
    saldo = Column(Integer, nullable=False)  # existencias de la variante después del movimiento
    motivo = Column(String(200))
    compra_id = Column(Integer, ForeignKey("compra.id"))  # HU033
    pedido_id = Column(Integer, ForeignKey("pedido.id"))
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    variante = relationship("Variante")
    usuario = relationship("Usuario")
    pedido = relationship("Pedido")
