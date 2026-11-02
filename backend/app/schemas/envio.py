from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
# T-07 (HU026 E7): nombre de zona de 3 a 60 caracteres y costo de 0.00 a 999.99.
NombreZona = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=60)]
Costo = Annotated[Decimal, Field(ge=0, le=Decimal("999.99"), max_digits=10, decimal_places=2)]


# --- Panel (HU026) ---

class ZonaEnvioIn(BaseModel):
    nombre: NombreZona = Field(examples=["Lima — motorizado"])
    costo: Costo = Field(examples=["10.00"])  # 0 = envío gratis en esa zona
    activa: bool = True


class ZonaEnvioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    costo: Decimal = Field(examples=["10.00"])
    activa: bool
    num_distritos: int = 0
    # Solo al desactivar la zona: cuántos distritos quedan sin cobertura (HU026 E9).
    distritos_sin_cobertura: int | None = None


class DistritoIn(BaseModel):
    nombre: Nombre = Field(examples=["Miraflores"])
    zona_envio_id: int | None = Field(None, examples=[1])  # null = sin cobertura


class DistritoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    zona_envio_id: int | None
    con_cobertura: bool


class AsignarDistritosIn(BaseModel):
    """Distritos que pasan a la zona (los demás distritos de la zona no se tocan)."""

    distrito_ids: list[int] = Field(min_length=1, examples=[[1, 2, 3]])
    # HU026 E8: true = mover a esta zona los distritos que ya estaban en otra. Sin él, eso responde 409.
    confirmar_traslado: bool = False


# --- Público, para el checkout (sin login) ---

class DistritoPublico(BaseModel):
    id: int
    nombre: str
    con_cobertura: bool
    costo_envio: Decimal | None = Field(examples=["10.00"])


class CostoEnvioOut(BaseModel):
    distrito_id: int
    distrito: str
    con_cobertura: bool
    costo_envio: Decimal | None = Field(examples=["10.00"])
