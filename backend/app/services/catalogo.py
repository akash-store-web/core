import logging

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
from app.services.carrito import disponibles_para_venta
from app.services.productos import VARIANTE_UNICA, foto_principal

log = logging.getLogger("akash.catalogo")

LIMITE_MAXIMO = 100


def _activas(producto: Producto) -> list:
    """HU028 E8: las variantes desactivadas (con historial, retiradas del panel) no existen para la clienta."""
    return [v for v in producto.variantes if v.activa]


def _es_listable(producto: Producto) -> bool:
    """HU001 E7 / HU002 E8: un producto publicado sin variantes o con algún precio efectivo <= 0 no se muestra.
    No debería pasar (publicar exige variante y precio > 0), pero si los datos se dañan, se oculta y se avisa."""
    if not _activas(producto):
        log.warning("Producto publicado %s sin variantes: se oculta del catálogo", producto.id)
        return False
    if any(v.precio_efectivo is None or v.precio_efectivo <= 0 for v in _activas(producto)):
        log.warning("Producto publicado %s con precio efectivo <= 0: se oculta del catálogo", producto.id)
        return False
    return True


def _tarjeta(producto: Producto, disponibles: dict[int, int]) -> dict:
    """`disponibles`: unidades vendibles por variante (existencias - reservas, nunca negativas)."""
    con_stock = [v for v in _activas(producto) if disponibles.get(v.id, 0) > 0]
    # HU002 E7: el precio "desde" sale de las variantes que se pueden comprar; si todas están agotadas, de todas.
    precios = {v.precio_efectivo for v in (con_stock or _activas(producto))}
    foto, generica = foto_principal(producto.imagenes)
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "categoria_id": producto.categoria_id,
        "categoria": producto.categoria.nombre,
        "precio": min(precios),
        "precio_desde": len(precios) > 1,
        "disponible": bool(con_stock),
        "es_pieza_natural": producto.es_pieza_natural,
        "foto_principal": foto,
        "foto_generica": generica,
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


def listar_catalogo(db: Session, categoria_id: int | None = None, q: str | None = None,
                    solo_disponibles: bool = False, limite: int = LIMITE_MAXIMO,
                    desde: int = 0) -> list[ProductoCatalogo]:
    consulta = _publicados(db).join(Producto.categoria).order_by(Categoria.orden, Producto.nombre)
    if categoria_id is not None:
        consulta = consulta.filter(Producto.categoria_id == categoria_id)
    if q and q.strip():
        consulta = consulta.filter(Producto.nombre.ilike(f"%{q.strip()}%"))
    productos = [p for p in consulta.all() if _es_listable(p)]
    disponibles = disponibles_para_venta(db, [v for p in productos for v in _activas(p)])
    tarjetas = [ProductoCatalogo(**_tarjeta(p, disponibles)) for p in productos]
    if solo_disponibles:  # HU029: ocultar los agotados (los que no tienen ninguna variante con stock)
        tarjetas = [t for t in tarjetas if t.disponible]
    # HU029 Esc.2: los agotados van al final. sorted es estable: dentro de cada grupo se conserva
    # el orden de la consulta (categoría.orden y luego nombre).
    tarjetas.sort(key=lambda t: not t.disponible)
    # HU001: paginación simple, después de ordenar para que las páginas sean coherentes.
    return tarjetas[desde:desde + limite]


def obtener_ficha(db: Session, producto_id: int) -> FichaProducto:
    producto = _publicados(db).filter(Producto.id == producto_id).first()
    if producto is None or not _es_listable(producto):  # despublicado o con datos dañados: no existe para la clienta
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    variantes = _activas(producto)
    disponibles = disponibles_para_venta(db, variantes)
    return FichaProducto(
        **_tarjeta(producto, disponibles),
        descripcion=producto.descripcion,
        material=producto.material,
        medidas=producto.medidas,
        peso_g=producto.peso_g,
        tiene_variantes=not (len(variantes) == 1 and variantes[0].nombre == VARIANTE_UNICA),
        variantes=[
            VariantePublica(id=v.id, nombre=v.nombre, precio=v.precio_efectivo,
                            disponible=disponibles.get(v.id, 0) > 0,
                            ultima_unidad=disponibles.get(v.id, 0) == 1,  # HU003 Esc.4, sin exponer la cantidad
                            propiedades=v.propiedades)
            for v in variantes
        ],
        imagenes=[
            ImagenPublica(url=i.url, es_principal=i.es_principal, es_referencia_escala=i.es_referencia_escala)
            for i in producto.imagenes
        ],
    )
