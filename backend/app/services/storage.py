"""Cliente mínimo de Supabase Storage (API HTTP). Solo el backend tiene la llave secreta."""
import httpx

from app import config


def _headers(extra: dict | None = None) -> dict:
    if not (config.SUPABASE_URL and config.SUPABASE_SECRET_KEY):
        raise RuntimeError("SUPABASE_URL y SUPABASE_SECRET_KEY deben estar configuradas")
    clave = config.SUPABASE_SECRET_KEY
    return {"apikey": clave, "Authorization": f"Bearer {clave}", **(extra or {})}


def url_publica(ruta: str) -> str:
    return f"{config.SUPABASE_URL}/storage/v1/object/public/{config.SUPABASE_BUCKET}/{ruta}"


def ruta_desde_url(url: str) -> str | None:
    prefijo = url_publica("")
    return url[len(prefijo):] if url.startswith(prefijo) else None


def subir(ruta: str, contenido: bytes, content_type: str) -> str:
    """Sube el archivo y devuelve su URL pública (el bucket es público para el catálogo)."""
    respuesta = httpx.post(
        f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_BUCKET}/{ruta}",
        content=contenido,
        headers=_headers({"Content-Type": content_type, "x-upsert": "false"}),
        timeout=30,
    )
    respuesta.raise_for_status()
    return url_publica(ruta)


def borrar(ruta: str) -> None:
    respuesta = httpx.request(
        "DELETE",
        f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_BUCKET}",
        json={"prefixes": [ruta]},
        headers=_headers(),
        timeout=30,
    )
    respuesta.raise_for_status()
