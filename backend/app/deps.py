import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import JWT_SECRET
from app.database import get_db
from app.models.usuario import Usuario
from app.services.auth import ALGORITHM

bearer = HTTPBearer(auto_error=False)


def _no_autorizado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Protege las rutas del panel: exige un JWT válido de un usuario activo."""
    if credenciales is None:
        raise _no_autorizado("No autenticado")
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET no está configurado")
    try:
        payload = jwt.decode(
            credenciales.credentials,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise _no_autorizado("Token expirado")
    except (jwt.InvalidTokenError, ValueError):
        raise _no_autorizado("Token inválido")

    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        raise _no_autorizado("Usuario no válido")
    return usuario


def get_current_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Protege las rutas /admin. Hoy toda cuenta es de la propietaria; cuando la tabla
    usuario tenga la columna rol, aquí se exige rol admin (403 para cliente o proveedor)."""
    return usuario
