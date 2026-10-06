from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app import config
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.variante import Variante
from app.schemas.producto import ProductoCrear, ProductoIn, ProductoListItem

VARIANTE_UNICA = "Única"


def obtener_producto(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return producto


def _validar_categoria(db: Session, categoria_id: int) -> None:
    if db.get(Categoria, categoria_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La categoría no existe")


def crear_producto(db: Session, datos: ProductoCrear) -> Producto:
    _validar_categoria(db, datos.categoria_id)
    producto = Producto(**datos.model_dump(exclude={"existencias"}))
    # HU027 #3: un producto sin variantes funciona con una variante única implícita.
    producto.variantes.append(Variante(nombre=VARIANTE_UNICA, existencias=datos.existencias))
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


def cambiar_publicado(db: Session, producto_id: int, publicado: bool) -> Producto:
    """HU016: ocultar un producto del catálogo sin eliminarlo. Despublicar siempre se permite;
    publicar exige que el producto esté completo para la clienta."""
    producto = obtener_producto(db, producto_id)
    if publicado:
        faltantes = []
        if not producto.variantes:
            faltantes.append("al menos una variante")
        if config.PUBLICAR_EXIGE_FOTO and not producto.imagenes:
            faltantes.append("al menos una foto")
        if faltantes:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No se puede publicar: falta " + " y ".join(faltantes),
            )
    producto.publicado = publicado
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
        existencias_total = sum(v.existencias for v in p.variantes)
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
                existencias_total=existencias_total,
                agotado=existencias_total == 0,
                foto_principal=principal.url if principal else None,
            )
        )
    return filas
