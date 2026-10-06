from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Variante(Base):
    __tablename__ = "variante"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=False)
    nombre = Column(String(80), nullable=False)
    precio = Column(Numeric(10, 2))  # NULL = hereda producto.precio_base
    existencias = Column(Integer, nullable=False, default=0, server_default="0")
    propiedades = Column(Text)

    producto = relationship("Producto", back_populates="variantes")

    @property
    def agotado(self) -> bool:
        return self.existencias <= 0

    @property
    def precio_efectivo(self):
        """Precio con el que se vende: el propio de la variante o, si no tiene, el del producto."""
        return self.precio if self.precio is not None else self.producto.precio_base
