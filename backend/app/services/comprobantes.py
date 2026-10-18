"""HU033 (AKASH-115): comprobante de la compra (foto o PDF) en un bucket privado de Supabase."""
import logging
import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.compra import Compra
from app.services import storage

log = logging.getLogger("akash.comprobantes")

MAX_BYTES = 5 * 1024 * 1024
TIPOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}
ENLACE_SEGUNDOS = 300  # el enlace para ver el comprobante dura 5 minutos


def _tipo_real(contenido: bytes) -> str | None:
    """Revisa la firma del archivo: no basta con el Content-Type que declara el navegador."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def _obtener_compra(db: Session, compra_id: int) -> Compra:
    compra = db.get(Compra, compra_id)
    if compra is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    return compra


def adjuntar_comprobante(db: Session, compra_id: int, contenido: bytes) -> None:
    compra = _obtener_compra(db, compra_id)
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "El comprobante no puede superar 5 MB")
    tipo = _tipo_real(contenido)
    if tipo is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Solo se aceptan fotos JPG, PNG, WEBP o PDF")

    ruta = f"compras/{compra_id}/{uuid.uuid4().hex}.{TIPOS[tipo]}"
    try:
        storage.subir_privado(ruta, contenido, tipo)
    except httpx.HTTPError as error:
        log.error("No se pudo subir %s a Storage: %s", ruta, error)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo guardar el comprobante; intentalo de nuevo")

    anterior = compra.comprobante_url
    compra.comprobante_url = ruta
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.borrar_privado(ruta)  # no dejar archivos huerfanos en el bucket
        raise
    if anterior:  # si se reemplaza el comprobante, se borra el viejo
        try:
            storage.borrar_privado(anterior)
        except httpx.HTTPError as error:
            log.warning("No se pudo borrar %s de Storage: %s", anterior, error)


def enlace_comprobante(db: Session, compra_id: int) -> dict:
    compra = _obtener_compra(db, compra_id)
    if not compra.comprobante_url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta compra no tiene comprobante adjunto")
    try:
        url = storage.url_firmada(compra.comprobante_url, ENLACE_SEGUNDOS)
    except httpx.HTTPError as error:
        log.error("No se pudo firmar %s: %s", compra.comprobante_url, error)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo generar el enlace; intentalo de nuevo")
    return {"url": url, "expira_en_segundos": ENLACE_SEGUNDOS}