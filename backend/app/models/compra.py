from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class TipoComprobante:
    BOLETA = "boleta"
    FACTURA = "factura"
    TODOS = (BOLETA, FACTURA)


class Compra(Base):
    """HU033: compra de mercadería respaldada por su boleta o factura
    (docs/sql/2026-10_sprint2_compras_y_movimientos.sql)."""

    __tablename__ = "compra"

    id = Column(Integer, primary_key=True)
    proveedor = Column(String(120), nullable=False)
    proveedor_ruc = Column(String(11))
    tipo_comprobante = Column(String(10), nullable=False)
    numero_comprobante = Column(String(30), nullable=False)
    fecha = Column(Date, nullable=False)
    comprobante_url = Column(String(255))  # ruta en el bucket privado (AKASH-115)
    total = Column(Numeric(10, 2), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    detalles = relationship("DetalleCompra", back_populates="compra", order_by="DetalleCompra.id")
    usuario = relationship("Usuario")

    __table_args__ = (
        # Escenario 5: el mismo comprobante del mismo proveedor no se registra dos veces.
        Index("ux_compra_comprobante", func.lower(proveedor), tipo_comprobante, func.upper(numero_comprobante),
              unique=True),
    )


class DetalleCompra(Base):
    __tablename__ = "detalle_compra"

    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey("compra.id"), nullable=False)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(10, 2), nullable=False)

    compra = relationship("Compra", back_populates="detalles")
    variante = relationship("Variante")
