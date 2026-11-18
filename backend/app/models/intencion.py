"""HU005 / HU008: intenciones por piedra (docs/sql/2026-11_sprint3_intenciones.sql).

Van por VARIANTE, no por producto: cada piedra es una variante (la Pulsera de cuarzo tiene 12 piedras).
Idénticos a Supabase: `intencion.id` es INTEGER y `variante_intencion.intencion_id` es SMALLINT.
La tabla vieja `producto_intencion` (vacía) no se modela.
"""
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, SmallInteger, String

from app.database import Base


class Intencion(Base):
    __tablename__ = "intencion"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(60), nullable=False, unique=True)
    # HU005 E5: una intención desactivada deja de mostrarse en la ficha y en los filtros, sin borrar asignaciones.
    activa = Column(Boolean, nullable=False, default=True, server_default="true")


class VarianteIntencion(Base):
    """Intenciones de cada piedra. PK compuesta = sin repetir (HU008 E5). En Supabase un trigger impide
    más de 5 por variante; en SQLite no existe, por eso el backend valida el máximo (services/intenciones.py)."""

    __tablename__ = "variante_intencion"
    __table_args__ = (Index("ix_vi_intencion", "intencion_id"),)

    variante_id = Column(Integer, ForeignKey("variante.id", ondelete="CASCADE"), primary_key=True)
    intencion_id = Column(SmallInteger, ForeignKey("intencion.id"), primary_key=True)
