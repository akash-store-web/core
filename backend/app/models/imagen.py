from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Imagen(Base):
    __tablename__ = "imagen"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=False)
    url = Column(String(255), nullable=False)
    orden = Column(Integer, nullable=False, default=0, server_default="0")
    es_principal = Column(Boolean, nullable=False, default=False, server_default="false")
    es_referencia_escala = Column(Boolean, nullable=False, default=False, server_default="false")

    producto = relationship("Producto", back_populates="imagenes")
