"""HU008: asignar intenciones a una piedra (variante) desde el panel."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.intencion import Intencion
from app.services.movimientos import obtener_variante
from app.services.productos import marcar_modificado

# HU008 E6. En Supabase también lo impide el trigger tg_max_5_intenciones (en SQLite no existe).
MAX_INTENCIONES = 5


def listar_intenciones(db: Session) -> list[Intencion]:
    """Activas e inactivas, por nombre (el selector del formulario decide cómo mostrar las inactivas)."""
    return db.query(Intencion).order_by(Intencion.nombre).all()


def activas(intenciones: list[Intencion]) -> list[Intencion]:
    """HU005 E5: una intención desactivada deja de mostrarse (la asignación se conserva en la base)."""
    return [i for i in intenciones if i.activa]


def asignar_intenciones(db: Session, variante_id: int, intencion_ids: list[int]) -> list[Intencion]:
    """Reemplaza el conjunto. Repetidas se guardan una vez (E5); más de 5 distintas → 422 (E6);
    inexistente o inactiva → 422 indicando cuál (E4). Las inactivas que ya tuviera la piedra se quitan."""
    variante = obtener_variante(db, variante_id)  # 404 si no existe
    ids = list(dict.fromkeys(intencion_ids))  # sin repetir, conservando el orden
    if len(ids) > MAX_INTENCIONES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Máximo {MAX_INTENCIONES} intenciones por piedra")
    encontradas = {i.id: i for i in db.query(Intencion).filter(Intencion.id.in_(ids)).all()} if ids else {}
    no_existen = [i for i in ids if i not in encontradas]
    if no_existen:
        lista = ", ".join(map(str, no_existen))
        mensaje = f"La intención {lista} no existe" if len(no_existen) == 1 else f"Las intenciones {lista} no existen"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, mensaje)
    inactivas = [encontradas[i] for i in ids if not encontradas[i].activa]
    if inactivas:
        lista = ", ".join(f"«{i.nombre}» (id {i.id})" for i in inactivas)
        mensaje = (f"La intención {lista} está desactivada" if len(inactivas) == 1
                   else f"Las intenciones {lista} están desactivadas")
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, mensaje)

    variante.intenciones = [encontradas[i] for i in ids]
    marcar_modificado(variante.producto)
    db.commit()
    db.refresh(variante)
    return activas(variante.intenciones)
