from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.categoria import Categoria
from app.models.producto import Producto
from app.schemas.catalogo import (
    CategoriaPublica,
    FichaProducto,
    ImagenPublica,
    ProductoCatalogo,
    VariantePublica,
)
from app.services.productos import VARIANTE_UNICA


def _foto_principal(producto: Producto) -> str | None:
    principal = next((i for i in producto.imagenes if i.es_principal), None)
    principal = principal or (producto.imagenes[0] if producto.imagenes else None)
    return principal.url if principal else None


def _tarjeta(producto: Producto) -> dict:
    precios = {v.precio_efectivo for v in producto.variantes} or {producto.precio_base}
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "categoria_id": producto.categoria_id,
        "categoria": producto.categoria.nombre,
        "precio": min(precios),
        "precio_desde": len(precios) > 1,
        "disponible": any(not v.agotado for v in producto.variantes),
        "es_pieza_natural": producto.es_pieza_natural,
        "foto_principal": _foto_principal(producto),
    }


def _publicados(db: Session):
    return (
        db.query(Producto)
        .filter(Producto.publicado.is_(True))
        .options(selectinload(Producto.categoria), selectinload(Producto.variantes), selectinload(Producto.imagenes))
    )


def listar_categorias(db: Session) -> list[CategoriaPublica]:
    """Solo las categorías que tienen al menos un producto publicado, en el orden definido."""
    categorias = (
        db.query(Categoria)
        .filter(Categoria.id.in_(db.query(Producto.categoria_id).filter(Producto.publicado.is_(True))))
        .order_by(Categoria.orden)
        .all()
    )
    return [CategoriaPublica(id=c.id, nombre=c.nombre) for c in categorias]


def listar_catalogo(db: Session, categoria_id: int | None = None, q: str | None = None) -> list[ProductoCatalogo]:
    consulta = _publicados(db).join(Producto.categoria).order_by(Categoria.orden, Producto.nombre)
    if categoria_id is not None:
        consulta = consulta.filter(Producto.categoria_id == categoria_id)
    if q and q.strip():
        consulta = consulta.filter(Producto.nombre.ilike(f"%{q.strip()}%"))
    return [ProductoCatalogo(**_tarjeta(p)) for p in consulta.all()]


def obtener_ficha(db: Session, producto_id: int) -> FichaProducto:
    producto = _publicados(db).filter(Producto.id == producto_id).first()
    if producto is None:  # un producto despublicado no existe para la clienta
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    variantes = producto.variantes
    return FichaProducto(
        **_tarjeta(producto),
        descripcion=producto.descripcion,
        material=producto.material,
        medidas=producto.medidas,
        peso_g=producto.peso_g,
        tiene_variantes=not (len(variantes) == 1 and variantes[0].nombre == VARIANTE_UNICA),
        variantes=[
            VariantePublica(id=v.id, nombre=v.nombre, precio=v.precio_efectivo, disponible=not v.agotado,
                            propiedades=v.propiedades)
            for v in variantes
        ],
        imagenes=[
            ImagenPublica(url=i.url, es_principal=i.es_principal, es_referencia_escala=i.es_referencia_escala)
            for i in producto.imagenes
        ],
    )
