"""Catálogo público: sin login. La clienta navega y compra sin crear cuenta."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.catalogo import CategoriaPublica, FichaProducto, ProductoCatalogo
from app.services import catalogo as servicio

router = APIRouter(prefix="/catalogo", tags=["catálogo (público)"])


@router.get("", response_model=list[ProductoCatalogo])
def listar_catalogo(categoria_id: int | None = None, q: str | None = None, solo_disponibles: bool = False,
                    limite: int = Query(servicio.LIMITE_MAXIMO, ge=1, le=servicio.LIMITE_MAXIMO),
                    desde: int = Query(0, ge=0),
                    db: Session = Depends(get_db)):
    """Solo productos publicados (HU016), con precio visible (HU002) y disponibilidad (HU003).
    Los agotados van al final; `solo_disponibles=true` los oculta (HU029).
    Paginación opcional (HU001): `limite` 1-100 y `desde` (posición inicial, desde 0)."""
    return servicio.listar_catalogo(db, categoria_id, q, solo_disponibles, limite, desde)


@router.get("/categorias", response_model=list[CategoriaPublica])
def listar_categorias(db: Session = Depends(get_db)):
    return servicio.listar_categorias(db)


@router.get("/{producto_id}", response_model=FichaProducto)
def obtener_ficha(producto_id: int, db: Session = Depends(get_db)):
    return servicio.obtener_ficha(db, producto_id)
