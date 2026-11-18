"""HU019: ventas del mes.

Una venta cuenta en el mes (hora de Lima) en que se CONFIRMÓ, según el historial de estados, y solo si el
pedido sigue confirmado, enviado o entregado (un confirmado que luego se canceló ya no suma, E7)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.pedido import EstadoPedido, HistorialEstadoPedido, Pedido
from app.schemas.ventas import ResumenMes, VentasMesOut

# Perú no tiene horario de verano: offset fijo (en Windows zoneinfo puede no tener tzdata).
LIMA = timezone(timedelta(hours=-5), "America/Lima")
ESTADOS_VENTA = (EstadoPedido.CONFIRMADO, EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO)
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")
CENTIMOS = Decimal("0.01")


def nombre_mes(anio: int, mes: int) -> str:
    return f"{MESES[mes - 1]} de {anio}"


def mes_anterior(anio: int, mes: int) -> tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def mes_siguiente(anio: int, mes: int) -> tuple[int, int]:
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def mes_lima(fecha: datetime) -> tuple[int, int]:
    """(año, mes) de una fecha en hora de Lima. SQLite (pruebas) devuelve fechas sin zona: son UTC."""
    fecha = fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)
    local = fecha.astimezone(LIMA)
    return local.year, local.month


def _limites_utc(anio: int, mes: int) -> tuple[datetime, datetime]:
    """Inicio (incluido) y fin (excluido) del mes en hora de Lima, expresados en UTC."""
    inicio = datetime(anio, mes, 1, tzinfo=LIMA)
    fin = datetime(*mes_siguiente(anio, mes), 1, tzinfo=LIMA)
    return inicio.astimezone(timezone.utc), fin.astimezone(timezone.utc)


def _resumen(db: Session, anio: int, mes: int) -> ResumenMes:
    inicio, fin = _limites_utc(anio, mes)
    # Fecha de confirmación de cada pedido (la primera, por si acaso).
    confirmados = (
        db.query(HistorialEstadoPedido.pedido_id, func.min(HistorialEstadoPedido.fecha).label("confirmado_en"))
        .filter(HistorialEstadoPedido.estado == EstadoPedido.CONFIRMADO)
        .group_by(HistorialEstadoPedido.pedido_id)
        .subquery()
    )
    pedidos, productos, envio = (
        db.query(func.count(Pedido.id), func.sum(Pedido.subtotal), func.sum(Pedido.costo_envio))
        .join(confirmados, confirmados.c.pedido_id == Pedido.id)
        .filter(Pedido.estado.in_(ESTADOS_VENTA),
                confirmados.c.confirmado_en >= inicio, confirmados.c.confirmado_en < fin)
        .one()
    )
    productos = Decimal(productos or 0).quantize(CENTIMOS)
    envio = Decimal(envio or 0).quantize(CENTIMOS)
    return ResumenMes(anio=anio, mes=mes, pedidos=pedidos, total_productos=productos, total_envio=envio,
                      total=productos + envio)


def ventas_del_mes(db: Session, anio: int | None = None, mes: int | None = None) -> VentasMesOut:
    actual = mes_lima(datetime.now(timezone.utc))
    if (anio is None) != (mes is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Indica el año y el mes juntos")
    if anio is None:
        anio, mes = actual
    if not 1 <= mes <= 12:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El mes debe estar entre 1 y 12")
    if not 2000 <= anio <= 9999:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Año no válido")
    if (anio, mes) > actual:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No se puede consultar un mes futuro")

    # E5: no se consultan meses anteriores al primer pedido registrado; sin pedidos, solo el mes actual.
    primero = db.query(func.min(Pedido.fecha)).scalar()
    desde = mes_lima(primero) if primero is not None else actual
    if (anio, mes) < desde:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"No hay registros antes de {nombre_mes(*desde)}")

    resumen = _resumen(db, anio, mes)
    sin_ventas = resumen.pedidos == 0
    return VentasMesOut(
        **resumen.model_dump(), sin_ventas=sin_ventas,
        mensaje=f"No hubo ventas confirmadas en {nombre_mes(anio, mes)}" if sin_ventas else None,
        mes_anterior=_resumen(db, *mes_anterior(anio, mes)),
    )
