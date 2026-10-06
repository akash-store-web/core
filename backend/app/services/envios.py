from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.distrito import Distrito
from app.models.zona_envio import ZonaEnvio
from app.schemas.envio import AsignarDistritosIn, DistritoIn, ZonaEnvioIn, ZonaEnvioOut


# --- Zonas ---

def _zona_out(zona: ZonaEnvio) -> ZonaEnvioOut:
    return ZonaEnvioOut(id=zona.id, nombre=zona.nombre, costo=zona.costo, activa=zona.activa,
                        num_distritos=len(zona.distritos))


def obtener_zona(db: Session, zona_id: int) -> ZonaEnvio:
    zona = db.get(ZonaEnvio, zona_id)
    if zona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zona de envío no encontrada")
    return zona


def listar_zonas(db: Session) -> list[ZonaEnvioOut]:
    zonas = db.query(ZonaEnvio).options(selectinload(ZonaEnvio.distritos)).order_by(ZonaEnvio.nombre).all()
    return [_zona_out(z) for z in zonas]


def crear_zona(db: Session, datos: ZonaEnvioIn) -> ZonaEnvioOut:
    zona = ZonaEnvio(**datos.model_dump())
    db.add(zona)
    db.commit()
    db.refresh(zona)
    return _zona_out(zona)


def actualizar_zona(db: Session, zona_id: int, datos: ZonaEnvioIn) -> ZonaEnvioOut:
    """Los cambios de costo se aplican de inmediato: el checkout siempre lee el costo vigente."""
    zona = obtener_zona(db, zona_id)
    for campo, valor in datos.model_dump().items():
        setattr(zona, campo, valor)
    db.commit()
    db.refresh(zona)
    return _zona_out(zona)


def asignar_distritos(db: Session, zona_id: int, datos: AsignarDistritosIn) -> ZonaEnvioOut:
    zona = obtener_zona(db, zona_id)
    ids = set(datos.distrito_ids)
    distritos = db.query(Distrito).filter(Distrito.id.in_(ids)).all()
    faltan = ids - {d.id for d in distritos}
    if faltan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Distritos no encontrados: {sorted(faltan)}")
    for distrito in distritos:
        distrito.zona_envio_id = zona.id
    db.commit()
    db.refresh(zona)
    return _zona_out(zona)


# --- Distritos ---

def _validar_nombre_unico(db: Session, nombre: str, excluir_id: int | None = None) -> None:
    consulta = db.query(Distrito).filter(func.lower(Distrito.nombre) == nombre.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Distrito.id != excluir_id)
    if consulta.first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un distrito con ese nombre")


def _validar_zona(db: Session, zona_id: int | None) -> None:
    if zona_id is not None and db.get(ZonaEnvio, zona_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La zona de envío no existe")


def listar_distritos(db: Session, zona_envio_id: int | None = None, sin_zona: bool = False) -> list[Distrito]:
    consulta = db.query(Distrito).options(selectinload(Distrito.zona)).order_by(Distrito.nombre)
    if sin_zona:
        consulta = consulta.filter(Distrito.zona_envio_id.is_(None))
    elif zona_envio_id is not None:
        consulta = consulta.filter(Distrito.zona_envio_id == zona_envio_id)
    return consulta.all()


def crear_distrito(db: Session, datos: DistritoIn) -> Distrito:
    _validar_nombre_unico(db, datos.nombre)
    _validar_zona(db, datos.zona_envio_id)
    distrito = Distrito(**datos.model_dump())
    db.add(distrito)
    db.commit()
    db.refresh(distrito)
    return distrito


def actualizar_distrito(db: Session, distrito_id: int, datos: DistritoIn) -> Distrito:
    distrito = obtener_distrito(db, distrito_id)
    _validar_nombre_unico(db, datos.nombre, excluir_id=distrito_id)
    _validar_zona(db, datos.zona_envio_id)
    for campo, valor in datos.model_dump().items():
        setattr(distrito, campo, valor)
    db.commit()
    db.refresh(distrito)
    return distrito


def obtener_distrito(db: Session, distrito_id: int) -> Distrito:
    distrito = db.get(Distrito, distrito_id)
    if distrito is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Distrito no encontrado")
    return distrito


# --- Cálculo para el checkout ---

def costo_envio(distrito: Distrito) -> Decimal | None:
    """Costo vigente del distrito, o None si no tiene cobertura (sin zona o zona inactiva)."""
    return distrito.zona.costo if distrito.con_cobertura else None


def calcular_costo_envio(db: Session, distrito_id: int) -> Decimal:
    """Para el pedido (HU010): falla si el distrito no tiene cobertura."""
    costo = costo_envio(obtener_distrito(db, distrito_id))
    if costo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El distrito no tiene cobertura de envío")
    return costo
