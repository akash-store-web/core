"""HU005 / HU008: intenciones por piedra."""
from pydantic import BaseModel, ConfigDict, Field


class IntencionOut(BaseModel):
    """Selector del formulario del panel (activas e inactivas)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    activa: bool


class IntencionBreve(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class IntencionesIn(BaseModel):
    """Reemplaza el conjunto de intenciones de la piedra (0 a 5 distintas; las repetidas cuentan una vez)."""

    # El tope de 5 distintas se valida en el servicio (HU008 E6); aquí solo se evita un cuerpo desmesurado.
    intencion_ids: list[int] = Field(max_length=50, examples=[[1, 4]])


class IntencionCatalogo(BaseModel):
    """Filtro del catálogo (HU008) y sugerencias cuando una búsqueda no da resultados (E7)."""

    id: int
    nombre: str
    productos: int  # productos publicados que aparecen al filtrar por esta intención
