import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.producto import PrecioOut

MAX_POR_LINEA = 10  # HU009 E6 / HU010: más unidades se piden escribiendo por WhatsApp


# --- Público: registrar el pedido (HU010) ---

class ItemPedidoIn(BaseModel):
    """Solo variante y cantidad: el precio lo pone siempre el servidor (HU010 E7).
    Si el navegador manda un precio, se ignora."""

    variante_id: int = Field(examples=[1])
    cantidad: Annotated[int, Field(gt=0, le=MAX_POR_LINEA)] = Field(examples=[2])


NOMBRE_COMPLETO_MAX = 120  # columna cliente.nombre VARCHAR(120)

# HU035: letras (con tildes, ñ, ü), y entre palabras un espacio, guion o apóstrofo: «María José», «D'Angelo»,
# «Pérez-Rojas». [^\W\d_] = cualquier letra Unicode (sin dígitos ni guion bajo).
_SOLO_LETRAS = re.compile(r"[^\W\d_]+(?:[ '’\-][^\W\d_]+)*")


def _limpiar(valor):
    """Une tildes sueltas (NFC), quita espacios de los extremos y deja uno solo entre palabras."""
    if not isinstance(valor, str):
        return valor
    return " ".join(unicodedata.normalize("NFC", valor).split())


class PedidoIn(BaseModel):
    """HU010 + HU035 (AKASH-209): nombre completo en tres campos, dirección obligatoria y solo delivery.
    La web no pide ni guarda el DNI: si la propietaria lo necesita, lo pide por WhatsApp."""

    nombres: Annotated[str, Field(min_length=2, max_length=40)] = Field(examples=["Ana María"])
    apellido_paterno: Annotated[str, Field(min_length=2, max_length=40)] = Field(examples=["Quispe"])
    apellido_materno: Annotated[str, Field(min_length=2, max_length=40)] = Field(examples=["Mamani"])
    celular: str = Field(pattern=r"^9\d{8}$", examples=["911111111"],
                         description="9 dígitos que empiezan con 9")
    distrito_id: int = Field(examples=[1])
    # El recojo se descartó (AKASH-211): siempre es delivery y siempre se cobra envío.
    modalidad_entrega: Literal["delivery"] = Field("delivery", examples=["delivery"])
    direccion: Annotated[str, Field(min_length=5, max_length=150)] = Field(examples=["Av. Ficticia 123, dpto. 4"])
    referencia: Annotated[str | None, Field(max_length=200)] = None
    items: list[ItemPedidoIn] = Field(min_length=1, max_length=50)

    @field_validator("nombres", "apellido_paterno", "apellido_materno", "direccion", mode="before")
    @classmethod
    def _normalizar(cls, valor):
        return _limpiar(valor)

    @field_validator("nombres", "apellido_paterno", "apellido_materno")
    @classmethod
    def _solo_letras(cls, valor: str) -> str:
        if not _SOLO_LETRAS.fullmatch(valor):
            raise ValueError("solo se aceptan letras, espacios, guion y apóstrofo (sin números ni símbolos)")
        return valor

    @field_validator("celular", mode="before")
    @classmethod
    def _recortar(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("referencia", mode="before")
    @classmethod
    def _vacio_es_nulo(cls, valor):
        if isinstance(valor, str):
            valor = _limpiar(valor)
            return valor or None
        return valor

    @model_validator(mode="after")
    def _nombre_cabe(self):
        if len(self.nombre_completo) > NOMBRE_COMPLETO_MAX:
            raise ValueError(f"El nombre completo no puede pasar de {NOMBRE_COMPLETO_MAX} caracteres")
        return self

    @property
    def nombre_completo(self) -> str:
        """Así se guarda en cliente.nombre (sin cambio de esquema) y se muestra: «Ana María Quispe Mamani»."""
        return f"{self.nombres} {self.apellido_paterno} {self.apellido_materno}"


class LineaPedidoOut(BaseModel):
    variante_id: int
    producto: str
    variante: str
    cantidad: int
    precio_unitario: PrecioOut
    subtotal: PrecioOut


class PedidoCreadoOut(BaseModel):
    """Lo necesario para armar el mensaje de WhatsApp y la confirmación (HU010 escenarios 1, 3 y E8)."""

    numero: str = Field(examples=["P-0001"])
    estado: str = Field(examples=["pendiente"])
    fecha: datetime
    nombre: str
    celular: str
    distrito: str
    modalidad_entrega: str
    direccion: str | None
    referencia: str | None
    items: list[LineaPedidoOut]
    subtotal: PrecioOut
    costo_envio: PrecioOut
    total: PrecioOut
    repetido: bool = False  # True = doble envío (E9): se devolvió el pedido ya registrado


# --- Panel (HU017) ---

class PedidoBandeja(BaseModel):
    """Fila de la bandeja de pedidos del panel (HU017)."""

    id: int
    numero: str
    fecha: datetime
    clienta: str
    telefono: str
    total: PrecioOut
    metodo_pago: str
    estado: str
    num_items: int  # unidades totales del pedido


class ClientaOut(BaseModel):
    nombre: str
    telefono: str
    correo: str | None
    direccion: str | None
    referencia: str | None


class ItemPedidoOut(BaseModel):
    variante_id: int
    producto_id: int
    producto: str
    variante: str
    cantidad: int
    precio_unitario: PrecioOut  # precio histórico: el del momento del pedido, aunque luego cambie
    subtotal: Decimal = Field(examples=["90.00"])


class CambioEstadoIn(BaseModel):
    """HU018: botones Confirmar venta / Cancelar / Enviado / Entregado del panel."""

    estado: Literal["confirmado", "cancelado", "enviado", "entregado"] = Field(examples=["confirmado"])


class CambioEstadoOut(BaseModel):
    estado: str
    fecha: datetime
    usuario: str | None  # email de quien lo cambió; None = la clienta o el sistema


class PedidoDetalle(BaseModel):
    id: int
    numero: str
    fecha: datetime
    estado: str
    clienta: ClientaOut
    distrito: str | None
    modalidad_entrega: str
    items: list[ItemPedidoOut]
    subtotal: PrecioOut
    costo_envio: PrecioOut
    total: PrecioOut
    metodo_pago: str
    historial: list[CambioEstadoOut]
