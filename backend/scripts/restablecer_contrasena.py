"""HU024, plan de emergencia: restablecer la contraseña de una cuenta sin correo.

Uso (desde backend/, con DATABASE_URL en .env):  python -m scripts.restablecer_contrasena
"""
import getpass

from app import models  # noqa: F401  registra todos los modelos para las relaciones
from app.database import SessionLocal
from app.models.usuario import Usuario
from app.services.auth import MAX_BYTES_BCRYPT, hash_password


def main() -> None:
    email = input("Email de la cuenta: ").strip().lower()
    password = getpass.getpass("Nueva contraseña: ")
    confirm = getpass.getpass("Repite la contraseña: ")

    if password != confirm:
        raise SystemExit("Las contraseñas no coinciden.")
    if len(password) < 8:
        raise SystemExit("Usa al menos 8 caracteres.")
    if len(password.encode("utf-8")) > MAX_BYTES_BCRYPT:
        raise SystemExit(f"La contraseña no puede superar {MAX_BYTES_BCRYPT} bytes.")

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(email=email).first()
        if usuario is None:
            raise SystemExit("No existe una cuenta con ese email.")
        usuario.password_hash = hash_password(password)
        db.commit()
        print("Contraseña actualizada.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
