import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import JWT_EXPIRE_MINUTES, JWT_SECRET

ALGORITHM = "HS256"
# bcrypt solo admite 72 bytes; la política de contraseñas se mantiene por debajo de ese límite.
MAX_BYTES_BCRYPT = 72
TIPO_RESTABLECER = "restablecer"
RESTABLECER_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    datos = password.encode("utf-8")
    if len(datos) > MAX_BYTES_BCRYPT:
        return False  # bcrypt 5 lanza ValueError; ninguna contraseña válida supera el límite
    return bcrypt.checkpw(datos, password_hash.encode("utf-8"))


def _secreto() -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET no está configurado")
    return JWT_SECRET


def create_access_token(user_id: int) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expira}, _secreto(), algorithm=ALGORITHM)


def huella_password(password_hash: str) -> str:
    """Huella corta del hash actual: al cambiar la contraseña, los enlaces de restablecimiento
    emitidos antes dejan de servir (un solo uso, sin guardar nada en la base)."""
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def create_reset_token(user_id: int, password_hash: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=RESTABLECER_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expira, "tipo": TIPO_RESTABLECER, "huella": huella_password(password_hash)}
    return jwt.encode(payload, _secreto(), algorithm=ALGORITHM)


def decode_reset_token(token: str) -> tuple[int, str] | None:
    """Devuelve (user_id, huella) si el token es de restablecimiento y está vigente."""
    try:
        payload = jwt.decode(token, _secreto(), algorithms=[ALGORITHM],
                             options={"require": ["exp", "sub", "tipo", "huella"]})
        if payload["tipo"] != TIPO_RESTABLECER:
            return None
        return int(payload["sub"]), payload["huella"]
    except (jwt.InvalidTokenError, ValueError):
        return None
