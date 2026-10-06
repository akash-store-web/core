from sqlalchemy import Column, Integer, String

from app.database import Base


class Cliente(Base):
    """Datos de contacto y entrega de cada compra (compra como invitada; no tiene credenciales)."""

    __tablename__ = "cliente"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    telefono = Column(String(20), nullable=False)
    correo = Column(String(120), nullable=False)
    direccion = Column(String(200), nullable=False)
    referencia = Column(String(200))
