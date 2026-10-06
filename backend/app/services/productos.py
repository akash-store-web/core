from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.categoria import Categoria
from app.models.producto import Producto
from app.schemas.producto import ProductoIn, ProductoListItem


def obtener_producto(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return producto


def _validar_categoria(db: Session, categoria_id: int) -> None:
    if db.get(Categoria, categoria_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La categoría no existe")


def crear_producto(db: Session, datos: ProductoIn) -> Producto:
    _validar_categoria(db, datos.categoria_id)
    producto = Producto(**datos.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(db: Session, producto_id: int, datos: ProductoIn) -> Producto:
    producto = obtener_producto(db, producto_id)
    _validar_categoria(db, datos.categoria_id)
    for campo, valor in datos.model_dump().items():
        setattr(producto, campo, valor)
    db.commit()
    db.refresh(producto)
    return producto


def listar_productos(db: Session, q: str | None = None, categoria_id: int | None = None) -> list[ProductoListItem]:
    consulta = (
        db.query(Producto)
        .options(selectinload(Producto.categoria), selectinload(Producto.variantes), selectinload(Producto.imagenes))
        .order_by(Producto.nombre)
    )
    if q and q.strip():
        consulta = consulta.filter(Producto.nombre.ilike(f"%{q.strip()}%"))
    if categoria_id is not None:
        consulta = consulta.filter(Producto.categoria_id == categoria_id)

    filas = []
    for p in consulta.all():
        principal = next((i for i in p.imagenes if i.es_principal), p.imagenes[0] if p.imagenes else None)
        filas.append(
            ProductoListItem(
                id=p.id,
                nombre=p.nombre,
                categoria_id=p.categoria_id,
                categoria=p.categoria.nombre,
                precio_base=p.precio_base,
                publicado=p.publicado,
                num_variantes=len(p.variantes),
                existencias_total=sum(v.existencias for v in p.variantes),
                foto_principal=principal.url if principal else None,
            )
        )
    return filas
