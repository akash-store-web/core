from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app import config
from app.models.imagen import Imagen
from app.models.categoria import Categoria
from app.models.producto import Producto, ahora
from app.models.variante import Variante
from app.schemas.producto import ProductoCrear, ProductoEditar, ProductoListItem

VARIANTE_UNICA = "Única"


def foto_principal(imagenes: list[Imagen]) -> tuple[str, bool]:
    """(url, es_generica): la foto marcada como principal, si no la primera, y si no hay fotos
    reales la imagen genérica. Así el frontend nunca recibe una foto vacía."""
    principal = next((i for i in imagenes if i.es_principal), imagenes[0] if imagenes else None)
    return (principal.url, False) if principal else (config.FOTO_GENERICA_URL, True)


def obtener_producto(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return producto


def _validar_categoria(db: Session, categoria_id: int) -> None:
    if db.get(Categoria, categoria_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La categoría no existe")


def marcar_modificado(producto: Producto) -> None:
    """HU032 E10: renueva la marca de edición. Se llama en cada cambio del producto, sus variantes o sus fotos."""
    producto.actualizado_en = ahora()


def _en_utc(fecha: datetime) -> datetime:
    # SQLite (pruebas) devuelve fechas sin zona; Postgres, con zona. Se comparan siempre en UTC.
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)


def _validar_nombre_unico(db: Session, categoria_id: int, nombre: str, excluir_id: int | None = None) -> None:
    """T-07 (HU014 E6): el nombre no se repite dentro de la categoría (sin mayúsculas ni espacios extremos)."""
    consulta = db.query(Producto).filter(
        Producto.categoria_id == categoria_id,
        func.lower(func.trim(Producto.nombre)) == nombre.strip().lower(),
    )
    if excluir_id is not None:
        consulta = consulta.filter(Producto.id != excluir_id)
    existente = consulta.first()
    if existente:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe un producto con ese nombre en la categoría: «{existente.nombre}» (id {existente.id})",
        )


def crear_producto(db: Session, datos: ProductoCrear) -> Producto:
    _validar_categoria(db, datos.categoria_id)
    _validar_nombre_unico(db, datos.categoria_id, datos.nombre)
    producto = Producto(**datos.model_dump())
    # HU027 #3: un producto sin variantes funciona con una variante única implícita.
    # HU034: nace sin stock; entra por compras o ajustes, nunca a mano.
    producto.variantes.append(Variante(nombre=VARIANTE_UNICA, existencias=0))
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(db: Session, producto_id: int, datos: ProductoEditar) -> Producto:
    producto = obtener_producto(db, producto_id)
    # HU032 E10: si el panel envía la marca que leyó y ya no coincide, alguien guardó antes.
    # Sin marca no se valida (compatibilidad con el frontend actual).
    if datos.actualizado_en is not None and _en_utc(datos.actualizado_en) != _en_utc(producto.actualizado_en):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Otra persona modificó este producto mientras lo editabas; recarga para ver los cambios y vuelve a guardar",
        )
    _validar_categoria(db, datos.categoria_id)
    _validar_nombre_unico(db, datos.categoria_id, datos.nombre, excluir_id=producto_id)
    for campo, valor in datos.model_dump(exclude={"actualizado_en"}).items():
        setattr(producto, campo, valor)
    marcar_modificado(producto)
    db.commit()
    db.refresh(producto)
    return producto


def cambiar_publicado(db: Session, producto_id: int, publicado: bool) -> Producto:
    """HU016: ocultar un producto del catálogo sin eliminarlo. Despublicar siempre se permite;
    publicar exige que el producto esté completo para la clienta."""
    producto = obtener_producto(db, producto_id)
    if publicado:
        faltantes = []
        if not any(v.activa for v in producto.variantes):
            faltantes.append("al menos una variante activa")
        if config.PUBLICAR_EXIGE_FOTO and not producto.imagenes:
            faltantes.append("al menos una foto")
        if faltantes:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No se puede publicar: falta " + " y ".join(faltantes),
            )
    if producto.publicado != publicado:  # publicar dos veces no cuenta como cambio (HU016 E7)
        producto.publicado = publicado
        marcar_modificado(producto)
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
        activas = [v for v in p.variantes if v.activa]
        existencias_total = sum(v.existencias for v in activas)
        foto, generica = foto_principal(p.imagenes)
        filas.append(
            ProductoListItem(
                id=p.id,
                nombre=p.nombre,
                categoria_id=p.categoria_id,
                categoria=p.categoria.nombre,
                precio_base=p.precio_base,
                publicado=p.publicado,
                num_variantes=len(activas),
                existencias_total=existencias_total,
                agotado=existencias_total == 0,
                foto_principal=foto,
                foto_generica=generica,
            )
        )
    return filas
