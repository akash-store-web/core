"""HU033: registrar la compra de mercadería con su comprobante. Cada línea suma stock con un
movimiento de tipo «compra» (HU034), todo en una sola transacción: o entra la compra completa o nada."""
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.compra import Compra, DetalleCompra
from app.models.movimiento_stock import TipoMovimiento
from app.models.variante import Variante
from app.schemas.compra import CompraIn, CompraOut, CompraResumen, IngresoPorCompra, LineaCompraOut
from app.services.movimientos import registrar_movimiento
from app.services.productos import obtener_producto

DUPLICADO = "Ese comprobante de ese proveedor ya está registrado; no se volvió a sumar el stock"


def _existe_comprobante(db: Session, datos: CompraIn) -> bool:
    return db.query(Compra.id).filter(
        func.lower(Compra.proveedor) == datos.proveedor.lower(),
        Compra.tipo_comprobante == datos.tipo_comprobante,
        func.upper(Compra.numero_comprobante) == datos.numero_comprobante.upper(),
    ).first() is not None


def registrar_compra(db: Session, datos: CompraIn, usuario_id: int) -> CompraOut:
    if _existe_comprobante(db, datos):
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICADO)

    ids = [i.variante_id for i in datos.items]
    existentes = {v.id for v in db.query(Variante.id).filter(Variante.id.in_(ids))}
    faltan = sorted(set(ids) - existentes)
    if faltan:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"No existen las variantes: {faltan}")

    compra = Compra(
        proveedor=datos.proveedor, proveedor_ruc=datos.proveedor_ruc, tipo_comprobante=datos.tipo_comprobante,
        numero_comprobante=datos.numero_comprobante, fecha=datos.fecha, usuario_id=usuario_id,
        total=sum((i.costo_unitario * i.cantidad for i in datos.items), Decimal("0.00")),
        detalles=[DetalleCompra(variante_id=i.variante_id, cantidad=i.cantidad, costo_unitario=i.costo_unitario)
                  for i in datos.items],
    )
    try:
        db.add(compra)
        db.flush()  # obtiene el id; el índice único frena un duplicado simultáneo
        for item in datos.items:
            registrar_movimiento(db, item.variante_id, item.cantidad, TipoMovimiento.COMPRA,
                                 compra_id=compra.id, usuario_id=usuario_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICADO)
    except Exception:
        db.rollback()
        raise
    return obtener_compra(db, compra.id)


def _consulta(db: Session):
    return db.query(Compra).options(
        selectinload(Compra.detalles).selectinload(DetalleCompra.variante).selectinload(Variante.producto),
        selectinload(Compra.usuario),
    )


def _resumen(c: Compra) -> dict:
    return {
        "id": c.id, "fecha": c.fecha, "proveedor": c.proveedor, "tipo_comprobante": c.tipo_comprobante,
        "numero_comprobante": c.numero_comprobante, "total": c.total,
        "unidades": sum(d.cantidad for d in c.detalles), "tiene_comprobante": bool(c.comprobante_url),
    }


def listar_compras(db: Session, proveedor: str | None = None, desde: date | None = None,
                   hasta: date | None = None) -> list[CompraResumen]:
    consulta = _consulta(db).order_by(Compra.fecha.desc(), Compra.id.desc())
    if proveedor and proveedor.strip():
        consulta = consulta.filter(Compra.proveedor.ilike(f"%{proveedor.strip()}%"))
    if desde:
        consulta = consulta.filter(Compra.fecha >= desde)
    if hasta:
        consulta = consulta.filter(Compra.fecha <= hasta)
    return [CompraResumen(**_resumen(c)) for c in consulta.all()]


def obtener_compra(db: Session, compra_id: int) -> CompraOut:
    compra = _consulta(db).filter(Compra.id == compra_id).first()
    if compra is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    return CompraOut(
        **_resumen(compra), proveedor_ruc=compra.proveedor_ruc, comprobante_url=compra.comprobante_url,
        usuario=compra.usuario.email if compra.usuario else None, creado_en=compra.creado_en,
        items=[
            LineaCompraOut(variante_id=d.variante_id, producto_id=d.variante.producto_id,
                           producto=d.variante.producto.nombre, variante=d.variante.nombre, cantidad=d.cantidad,
                           costo_unitario=d.costo_unitario, subtotal=d.costo_unitario * d.cantidad)
            for d in compra.detalles
        ],
    )


def compras_de_producto(db: Session, producto_id: int) -> list[IngresoPorCompra]:
    """HU033 escenario 4: las compras con las que ingresó el stock del producto (más reciente primero)."""
    producto = obtener_producto(db, producto_id)
    filas = (
        db.query(DetalleCompra, Compra)
        .join(Compra, DetalleCompra.compra_id == Compra.id)
        .filter(DetalleCompra.variante_id.in_([v.id for v in producto.variantes]))
        .options(selectinload(DetalleCompra.variante))
        .order_by(Compra.fecha.desc(), Compra.id.desc(), DetalleCompra.id)
        .all()
    )
    return [
        IngresoPorCompra(compra_id=c.id, fecha=c.fecha, proveedor=c.proveedor, tipo_comprobante=c.tipo_comprobante,
                         numero_comprobante=c.numero_comprobante, variante_id=d.variante_id, variante=d.variante.nombre,
                         cantidad=d.cantidad, costo_unitario=d.costo_unitario)
        for d, c in filas
    ]
