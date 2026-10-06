"""Catálogo público: sin login. La clienta navega y compra sin crear cuenta."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.catalogo import CategoriaPublica, FichaProducto, ProductoCatalogo
from app.services import catalogo as servicio

router = APIRouter(prefix="/catalogo", tags=["catálogo (público)"])


@router.get("", response_model=list[ProductoCatalogo])
def listar_catalogo(categoria_id: int | None = None, q: str | None = None, db: Session = Depends(get_db)):
    """Solo productos publicados (HU016), con precio visible (HU002) y disponibilidad (HU003, HU015)."""
    return servicio.listar_catalogo(db, categoria_id, q)


@router.get("/categorias", response_model=list[CategoriaPublica])
def listar_categorias(db: Session = Depends(get_db)):
    return servicio.listar_categorias(db)


@router.get("/{producto_id}", response_model=FichaProducto)
def obtener_ficha(producto_id: int, db: Session = Depends(get_db)):
    return servicio.obtener_ficha(db, producto_id)
