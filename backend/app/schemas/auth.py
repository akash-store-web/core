from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from app.services.auth import MAX_BYTES_BCRYPT


def _cabe_en_bcrypt(valor: str) -> str:
    if len(valor.encode("utf-8")) > MAX_BYTES_BCRYPT:
        raise ValueError(f"La contraseña no puede superar {MAX_BYTES_BCRYPT} bytes")
    return valor


# Política mínima de contraseñas (la misma de scripts/crear_propietaria.py).
NuevaContrasena = Annotated[str, StringConstraints(min_length=8), AfterValidator(_cabe_en_bcrypt)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
