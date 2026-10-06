from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Distrito(Base):
    __tablename__ = "distrito"

    id = Column(Integer, primary_key=True)
    zona_envio_id = Column(Integer, ForeignKey("zona_envio.id"))  # NULL = sin cobertura
    nombre = Column(String(60), nullable=False)

    zona = relationship("ZonaEnvio", back_populates="distritos")

    @property
    def con_cobertura(self) -> bool:
        return self.zona is not None and self.zona.activa
