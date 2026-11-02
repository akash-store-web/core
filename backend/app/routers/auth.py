from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import (
    CambiarContrasenaRequest,
    LoginRequest,
    Mensaje,
    RecuperarRequest,
    RestablecerRequest,
    TokenResponse,
)
from app.services.auth import (
    create_access_token,
    create_reset_token,
    decode_reset_token,
    hash_password,
    huella_password,
    verify_password,
)
from app.services.correo import enviar_enlace_recuperacion
from app.services.limites import bloqueo_login, limite_recuperar

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAJE_RECUPERAR = "Si el correo está registrado, te enviaremos un enlace para restablecer tu contraseña"


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """401 si el correo o la contraseña no coinciden. Tras 5 intentos fallidos en 15 minutos, el correo
    queda bloqueado 15 minutos (429), aunque luego llegue la contraseña correcta (HU023 E8)."""
    email = credentials.email.lower()
    minutos = bloqueo_login.minutos_restantes(email)
    if minutos:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Demasiados intentos fallidos; vuelve a intentarlo en {minutos} "
            f"{'minuto' if minutos == 1 else 'minutos'} o recupera tu contraseña",
            headers={"Retry-After": str(minutos * 60)},
        )
    user = db.query(Usuario).filter_by(email=email).first()
    if not user or not user.activo or not verify_password(credentials.password, user.password_hash):
        bloqueo_login.registrar_fallo(email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    bloqueo_login.limpiar(email)
    return TokenResponse(access_token=create_access_token(user.id))


# --- HU024: recuperar el acceso ---

@router.post("/recuperar", response_model=Mensaje, status_code=status.HTTP_202_ACCEPTED)
def recuperar(datos: RecuperarRequest, tareas: BackgroundTasks, db: Session = Depends(get_db)) -> Mensaje:
    """Envía un enlace de un solo uso (30 min). Responde lo mismo, y igual de rápido, exista o no
    el correo: el envío va en segundo plano para que el tiempo de respuesta no delate qué correos tienen cuenta.
    HU024 E8: como máximo 3 solicitudes por correo por hora; desde la cuarta responde lo mismo pero no envía nada."""
    email = datos.email.lower()
    if not limite_recuperar.permitir(email):
        return Mensaje(detail=MENSAJE_RECUPERAR)
    user = db.query(Usuario).filter_by(email=email).first()
    if user and user.activo:
        token = create_reset_token(user.id, user.password_hash)
        tareas.add_task(enviar_enlace_recuperacion, user.email, f"{config.FRONTEND_URL}/restablecer?token={token}")
    return Mensaje(detail=MENSAJE_RECUPERAR)


@router.post("/restablecer", response_model=Mensaje)
def restablecer(datos: RestablecerRequest, db: Session = Depends(get_db)) -> Mensaje:
    invalido = HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace no es válido o ya venció; solicita uno nuevo")
    decodificado = decode_reset_token(datos.token)
    if decodificado is None:
        raise invalido
    user_id, huella = decodificado
    user = db.get(Usuario, user_id)
    # La huella cambia con la contraseña: un enlace ya usado (o anterior a otro cambio) no sirve.
    if user is None or not user.activo or huella != huella_password(user.password_hash):
        raise invalido
    user.password_hash = hash_password(datos.nueva_contrasena)
    db.commit()
    return Mensaje(detail="Contraseña actualizada; ya puedes iniciar sesión")


@router.put("/contrasena", response_model=Mensaje)
def cambiar_contrasena(
    datos: CambiarContrasenaRequest,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Mensaje:
    """Cambiar la contraseña con la sesión iniciada (no exige rol: servirá a cualquier cuenta)."""
    if not verify_password(datos.actual, usuario.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta")
    if datos.nueva == datos.actual:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La nueva contraseña debe ser distinta de la actual")
    usuario.password_hash = hash_password(datos.nueva)
    db.commit()
    return Mensaje(detail="Contraseña actualizada")
