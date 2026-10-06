from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class Producto(Base):
    __tablename__ = "producto"

    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categoria.id"), nullable=False)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(Text, nullable=False)
    precio_base = Column(Numeric(10, 2), nullable=False)
    material = Column(String(80))
    medidas = Column(String(80))
    peso_g = Column(Numeric(8, 2))
    es_pieza_natural = Column(Boolean, nullable=False, default=False, server_default="false")
    publicado = Column(Boolean, nullable=False, default=False, server_default="false")
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    categoria = relationship("Categoria")
    variantes = relationship("Variante", back_populates="producto", order_by="Variante.id")
    imagenes = relationship("Imagen", back_populates="producto", order_by="Imagen.orden")
