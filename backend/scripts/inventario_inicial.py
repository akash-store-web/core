"""HU034: registra el stock que ya existía como movimiento de "inventario inicial" (una sola vez).

Antes de HU034 las existencias se cargaban a mano (catálogo real, panel). Desde HU034 el stock solo cambia
con movimientos, así que cada variante con existencias y SIN movimientos recibe uno de tipo
inventario_inicial por su stock actual. El saldo no cambia: solo queda respaldado en el historial.

- Idempotente: una variante que ya tiene algún movimiento se salta.
- Requiere que exista la tabla movimiento_stock (docs/sql/2026-10_sprint2_compras_y_movimientos.sql).

Uso (desde backend/, con DATABASE_URL en .env):
    python -m scripts.inventario_inicial            # simulación: no escribe nada
    python -m scripts.inventario_inicial --aplicar  # escribe
"""
import argparse

from sqlalchemy import inspect
from sqlalchemy.orm import Session, selectinload

from app import models  # noqa: F401  registra todos los modelos para las relaciones
from app.database import SessionLocal
from app.models.movimiento_stock import MovimientoStock, TipoMovimiento
from app.models.variante import Variante


def pendientes(db: Session) -> list[Variante]:
    con_movimientos = db.query(MovimientoStock.variante_id).distinct()
    return (
        db.query(Variante)
        .filter(Variante.existencias > 0, Variante.id.notin_(con_movimientos))
        .options(selectinload(Variante.producto))
        .order_by(Variante.producto_id, Variante.id)
        .all()
    )


def registrar(db: Session, aplicar: bool) -> int:
    variantes = pendientes(db)
    for v in variantes:
        print(f"  + {v.producto.nombre} / {v.nombre}: {v.existencias} u.")
        if aplicar:
            # El stock ya está en la variante: el movimiento lo respalda sin volver a sumarlo.
            db.add(MovimientoStock(variante_id=v.id, tipo=TipoMovimiento.INVENTARIO_INICIAL,
                                   cantidad=v.existencias, saldo=v.existencias,
                                   motivo="Stock existente antes de los movimientos (HU034)"))
    if aplicar:
        db.commit()
    unidades = sum(v.existencias for v in variantes)
    print(f"{'Registrados' if aplicar else 'Se registrarían'} {len(variantes)} movimientos ({unidades} unidades).")
    return len(variantes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aplicar", action="store_true", help="escribe en la base (sin esto solo simula)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if not inspect(db.get_bind()).has_table("movimiento_stock"):
            raise SystemExit("Falta la tabla movimiento_stock: ejecuta primero el SQL de docs/sql/. No se escribió nada.")
        print("MODO:", "APLICAR (escribe en la base)" if args.aplicar else "SIMULACIÓN (no escribe nada)")
        registrar(db, args.aplicar)
    finally:
        db.close()


if __name__ == "__main__":
    main()
