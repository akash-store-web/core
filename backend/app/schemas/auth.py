from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from app.services.auth import MAX_BYTES_BCRYPT


def _cabe_en_bcrypt(valor: str) -> str:
    if len(valor.encode("utf-8")) > MAX_BYTES_BCRYPT:
        raise ValueError(f"La contraseña no puede superar {MAX_BYTES_BCRYPT} bytes")
    return valor


def _letra_y_numero(valor: str) -> str:
    # T-07 (HU024 E5): al menos una letra y un número.
    if not any(c.isalpha() for c in valor) or not any(c.isdigit() for c in valor):
        raise ValueError("La contraseña debe tener al menos una letra y un número")
    return valor


# Política de contraseñas (la misma de scripts/crear_propietaria.py): mínimo 8, con letra y número.
NuevaContrasena = Annotated[str, StringConstraints(min_length=8), AfterValidator(_letra_y_numero),
                            AfterValidator(_cabe_en_bcrypt)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)  # vacía = 422, sin consultar la base (HU023 E5)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- HU024: recuperar el acceso ---

class RecuperarRequest(BaseModel):
    email: EmailStr = Field(examples=["propietaria@ejemplo.com"])


class RestablecerRequest(BaseModel):
    token: str
    nueva_contrasena: NuevaContrasena


class CambiarContrasenaRequest(BaseModel):
    actual: str
    nueva: NuevaContrasena


class Mensaje(BaseModel):
    detail: str
