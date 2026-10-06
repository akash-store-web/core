from sqlalchemy import Boolean, Column, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


class ZonaEnvio(Base):
    __tablename__ = "zona_envio"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(60), nullable=False)
    costo = Column(Numeric(10, 2), nullable=False)
    activa = Column(Boolean, nullable=False, default=True, server_default="true")

    distritos = relationship("Distrito", back_populates="zona", order_by="Distrito.nombre")
