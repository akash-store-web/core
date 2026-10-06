from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models.categoria import Categoria
from app.schemas.producto import CategoriaOut, ProductoCrear, ProductoIn, ProductoListItem, ProductoOut
from app.services import productos as servicio

router = APIRouter(prefix="/admin", tags=["admin: productos"], dependencies=[Depends(get_current_admin)])


@router.get("/categorias", response_model=list[CategoriaOut])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(Categoria).order_by(Categoria.orden).all()


@router.get("/productos", response_model=list[ProductoListItem])
def listar_productos(q: str | None = None, categoria_id: int | None = None, db: Session = Depends(get_db)):
    return servicio.listar_productos(db, q, categoria_id)


@router.post("/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(datos: ProductoCrear, db: Session = Depends(get_db)):
    return servicio.crear_producto(db, datos)


@router.get("/productos/{producto_id}", response_model=ProductoOut)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    return servicio.obtener_producto(db, producto_id)


@router.put("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(producto_id: int, datos: ProductoIn, db: Session = Depends(get_db)):
    return servicio.actualizar_producto(db, producto_id, datos)
