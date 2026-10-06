from sqlalchemy import Column, Integer, String

from app.database import Base


class Categoria(Base):
    __tablename__ = "categoria"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(60), nullable=False)
    orden = Column(Integer, nullable=False)
