"""HU014 (AKASH-42): fotos de producto. Máximo 5; la primera queda como principal."""
import logging
import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.imagen import Imagen
from app.services import storage
from app.services.productos import obtener_producto

log = logging.getLogger("akash.imagenes")

MAX_FOTOS = 5
MAX_BYTES = 5 * 1024 * 1024
TIPOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _tipo_real(contenido: bytes) -> str | None:
    """Revisa la firma del archivo: no basta con el Content-Type que declara el navegador."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


def _obtener_imagen(db: Session, producto_id: int, imagen_id: int) -> Imagen:
    imagen = db.get(Imagen, imagen_id)
    if imagen is None or imagen.producto_id != producto_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen no encontrada")
    return imagen


def subir_imagen(db: Session, producto_id: int, contenido: bytes) -> Imagen:
    producto = obtener_producto(db, producto_id)
    if len(producto.imagenes) >= MAX_FOTOS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El producto ya tiene {MAX_FOTOS} fotos; elimina una para subir otra")
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "La foto no puede superar 5 MB")
    tipo = _tipo_real(contenido)
    if tipo is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Solo se aceptan fotos JPG, PNG o WEBP")

    ruta = f"{producto_id}/{uuid.uuid4().hex}.{TIPOS[tipo]}"
    try:
        url = storage.subir(ruta, contenido, tipo)
    except httpx.HTTPError as error:
        log.error("No se pudo subir %s a Storage: %s", ruta, error)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo guardar la foto; inténtalo de nuevo")

    imagen = Imagen(
        producto_id=producto_id,
        url=url,
        orden=max((i.orden for i in producto.imagenes), default=-1) + 1,
        es_principal=not producto.imagenes,  # la primera foto queda como principal
    )
    db.add(imagen)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.borrar(ruta)  # no dejar archivos huérfanos en el bucket
        raise
    db.refresh(imagen)
    return imagen


def marcar_principal(db: Session, producto_id: int, imagen_id: int) -> list[Imagen]:
    elegida = _obtener_imagen(db, producto_id, imagen_id)
    for imagen in elegida.producto.imagenes:
        imagen.es_principal = imagen.id == elegida.id
    db.commit()
    return obtener_producto(db, producto_id).imagenes


def eliminar_imagen(db: Session, producto_id: int, imagen_id: int) -> None:
    imagen = _obtener_imagen(db, producto_id, imagen_id)
    producto = imagen.producto
    era_principal = imagen.es_principal
    ruta = storage.ruta_desde_url(imagen.url)
    db.delete(imagen)
    db.flush()
    if era_principal:
        restantes = [i for i in producto.imagenes if i.id != imagen_id]
        if restantes:
            min(restantes, key=lambda i: i.orden).es_principal = True
    db.commit()
    if ruta:
        try:
            storage.borrar(ruta)
        except httpx.HTTPError as error:  # el registro ya se borró; el archivo huérfano no afecta al catálogo
            log.warning("No se pudo borrar %s de Storage: %s", ruta, error)
