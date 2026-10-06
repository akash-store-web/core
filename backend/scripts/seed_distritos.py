"""HU026: carga inicial de los distritos de Lima Metropolitana y del Callao.

- Se cargan SIN zona (sin cobertura): la propietaria crea las zonas con sus costos reales
  (HU026 #4) y asigna los distritos desde el panel.
- Envío a provincia: pendiente de decisión de la propietaria (tarifa única o coordinar por WhatsApp).
- Idempotente: no duplica distritos que ya existan (sin distinguir mayúsculas).

Uso (desde backend/, con DATABASE_URL en .env):
    python -m scripts.seed_distritos            # simulación: no escribe nada
    python -m scripts.seed_distritos --aplicar  # carga en la base
"""
import argparse

from sqlalchemy import func

from app import models  # noqa: F401  registra todos los modelos para las relaciones
from app.database import SessionLocal
from app.models.distrito import Distrito

LIMA_METROPOLITANA = [
    "Ancón", "Ate", "Barranco", "Breña", "Carabayllo", "Cercado de Lima", "Chaclacayo", "Chorrillos",
    "Cieneguilla", "Comas", "El Agustino", "Independencia", "Jesús María", "La Molina", "La Victoria",
    "Lince", "Los Olivos", "Lurigancho-Chosica", "Lurín", "Magdalena del Mar", "Miraflores", "Pachacámac",
    "Pucusana", "Pueblo Libre", "Puente Piedra", "Punta Hermosa", "Punta Negra", "Rímac", "San Bartolo",
    "San Borja", "San Isidro", "San Juan de Lurigancho", "San Juan de Miraflores", "San Luis",
    "San Martín de Porres", "San Miguel", "Santa Anita", "Santa María del Mar", "Santa Rosa",
    "Santiago de Surco", "Surquillo", "Villa El Salvador", "Villa María del Triunfo",
]
CALLAO = [
    "Bellavista", "Callao", "Carmen de la Legua-Reynoso", "La Perla", "La Punta", "Mi Perú", "Ventanilla",
]
DISTRITOS = LIMA_METROPOLITANA + CALLAO


def cargar(db, aplicar: bool) -> int:
    existentes = {nombre for (nombre,) in db.query(func.lower(Distrito.nombre)).all()}
    nuevos = [nombre for nombre in DISTRITOS if nombre.lower() not in existentes]
    for nombre in nuevos:
        print(f"  + {nombre}")
        if aplicar:
            db.add(Distrito(nombre=nombre, zona_envio_id=None))
    if aplicar:
        db.commit()
    print(f"{'Creados' if aplicar else 'Se crearían'} {len(nuevos)} distritos "
          f"({len(DISTRITOS) - len(nuevos)} ya existían), todos sin cobertura.")
    return len(nuevos)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aplicar", action="store_true", help="escribe en la base (sin esto solo simula)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        print("MODO:", "APLICAR (escribe en la base)" if args.aplicar else "SIMULACIÓN (no escribe nada)")
        cargar(db, args.aplicar)
    finally:
        db.close()


if __name__ == "__main__":
    main()
