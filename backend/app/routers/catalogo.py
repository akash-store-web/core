"""Catálogo público: sin login. La clienta navega y compra sin crear cuenta."""
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.catalogo import CategoriaPublica, FichaProducto, ProductoCatalogo
from app.schemas.intencion import IntencionCatalogo
from app.schemas.producto import PRECIO_MAXIMO
from app.services import catalogo as servicio

router = APIRouter(prefix="/catalogo", tags=["catálogo (público)"])


@router.get("", response_model=list[ProductoCatalogo])
def listar_catalogo(categoria_id: int | None = None, q: str | None = None, solo_disponibles: bool = False,
                    limite: int = Query(servicio.LIMITE_MAXIMO, ge=1, le=servicio.LIMITE_MAXIMO),
                    desde: int = Query(0, ge=0),
                    intencion_id: int | None = None,
                    precio_min: Decimal | None = Query(None, ge=0, le=PRECIO_MAXIMO, max_digits=6, decimal_places=2),
                    precio_max: Decimal | None = Query(None, ge=0, le=PRECIO_MAXIMO, max_digits=6, decimal_places=2),
                    db: Session = Depends(get_db)):
    """Solo productos publicados (HU016), con precio visible (HU002) y disponibilidad (HU003).
    Los agotados van al final; `solo_disponibles=true` los oculta (HU029).
    Paginación opcional (HU001): `limite` 1-100 y `desde` (posición inicial, desde 0).
    `categoria_id` inexistente se ignora (HU007 E7).
    `intencion_id` (HU008): productos con al menos una piedra con esa intención; si no existe o está
    desactivada, la lista sale vacía.
    `precio_min` / `precio_max` (HU007): 0 a 9999.99; entra el producto si al menos una piedra activa tiene
    su precio en el rango. 422 si el mínimo es mayor que el máximo."""
    return servicio.listar_catalogo(db, categoria_id, q, solo_disponibles, limite, desde, intencion_id,
                                    precio_min, precio_max)


@router.get("/categorias", response_model=list[CategoriaPublica])
def listar_categorias(db: Session = Depends(get_db)):
    return servicio.listar_categorias(db)


@router.get("/intenciones", response_model=list[IntencionCatalogo])
def listar_intenciones(db: Session = Depends(get_db)):
    """HU008: intenciones activas con `productos` = cuántos productos salen al filtrar por cada una."""
    return servicio.listar_intenciones(db)


@router.get("/{producto_id}", response_model=FichaProducto)
def obtener_ficha(producto_id: int, db: Session = Depends(get_db)):
    return servicio.obtener_ficha(db, producto_id)
