import getpass

from app import models  # noqa: F401  registra todos los modelos para las relaciones
from app.database import SessionLocal
from app.models.usuario import Usuario
from app.services.auth import hash_password


def main() -> None:
    email = input("Email de la cuenta: ").strip().lower()
    password = getpass.getpass("Contraseña: ")
    confirm = getpass.getpass("Repite la contraseña: ")

    if password != confirm:
        raise SystemExit("Las contraseñas no coinciden.")
    if len(password) < 8:
        raise SystemExit("Usa al menos 8 caracteres.")
    if not email or "@" not in email:
        raise SystemExit("Ingresa un email válido.")

    # Las tablas las administra Diego en Supabase: aquí no se crean ni modifican.
    db = SessionLocal()
    try:
        if db.query(Usuario).filter_by(email=email).first():
            raise SystemExit("Ese email ya existe.")
        db.add(Usuario(email=email, password_hash=hash_password(password)))
        db.commit()
        print("Cuenta creada.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
