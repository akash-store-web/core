"""HU014 (AKASH-42): fotos de producto en Supabase Storage (simulado en las pruebas)."""
import httpx
import pytest

from app import config
from app.services import storage

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 100
COLLAR = {
    "categoria_id": 3,
    "nombre": "Collar de amatista",
    "descripcion": "Collar con dije de amatista natural.",
    "precio_base": "35.00",
}
URL = "/admin/productos/1/imagenes"


@pytest.fixture
def bucket(monkeypatch):
    """Storage en memoria: {ruta: bytes}."""
    archivos = {}
    monkeypatch.setattr(config, "SUPABASE_URL", "https://prueba.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_BUCKET", "productos")

    def subir(ruta, contenido, content_type):
        archivos[ruta] = contenido
        return storage.url_publica(ruta)

    monkeypatch.setattr(storage, "subir", subir)
    monkeypatch.setattr(storage, "borrar", lambda ruta: archivos.pop(ruta))
    return archivos


def _producto(client, auth):
    assert client.post("/admin/productos", json=COLLAR, headers=auth).status_code == 201


def _subir(client, auth, contenido=JPG, nombre="foto.jpg", tipo="image/jpeg"):
    return client.post(URL, files={"foto": (nombre, contenido, tipo)}, headers=auth)


def test_exige_token(client):
    assert client.post(URL, files={"foto": ("a.jpg", JPG, "image/jpeg")}).status_code == 401
    assert client.delete(f"{URL}/1").status_code == 401
    assert client.patch(f"{URL}/1/principal").status_code == 401


def test_la_primera_foto_es_la_principal(client, auth, bucket):
    _producto(client, auth)
    primera = _subir(client, auth)
    assert primera.status_code == 201
    assert primera.json()["es_principal"] is True
    assert primera.json()["url"].startswith("https://prueba.supabase.co/storage/v1/object/public/productos/1/")
    segunda = _subir(client, auth, PNG, "b.png", "image/png").json()
    assert (segunda["es_principal"], segunda["orden"]) == (False, 1)
    assert len(bucket) == 2
    assert client.get("/admin/productos", headers=auth).json()[0]["foto_principal"] == primera.json()["url"]


def test_acepta_jpg_png_y_webp(client, auth, bucket):
    _producto(client, auth)
    for contenido, nombre in ((JPG, "a.jpg"), (PNG, "b.png"), (WEBP, "c.webp")):
        assert _subir(client, auth, contenido, nombre).status_code == 201
    assert sorted(r.rsplit(".", 1)[1] for r in bucket) == ["jpg", "png", "webp"]


def test_maximo_cinco_fotos(client, auth, bucket):
    _producto(client, auth)
    for _ in range(5):
        assert _subir(client, auth).status_code == 201
    respuesta = _subir(client, auth)
    assert respuesta.status_code == 409
    assert len(bucket) == 5


def test_rechaza_archivos_que_no_son_fotos(client, auth, bucket):
    _producto(client, auth)
    # Aunque el navegador declare image/jpeg, se revisa la firma real del archivo.
    assert _subir(client, auth, b"%PDF-1.7 no soy una foto", "falso.jpg", "image/jpeg").status_code == 415
    assert _subir(client, auth, b"GIF89a" + b"0" * 50, "a.gif", "image/gif").status_code == 415
    assert bucket == {}


def test_rechaza_fotos_de_mas_de_5_mb(client, auth, bucket):
    _producto(client, auth)
    grande = JPG + b"0" * (5 * 1024 * 1024)
    assert _subir(client, auth, grande).status_code == 413
    assert bucket == {}


def test_producto_inexistente(client, auth, bucket):
    assert client.post("/admin/productos/99/imagenes", files={"foto": ("a.jpg", JPG, "image/jpeg")},
                       headers=auth).status_code == 404


def test_falla_de_storage_responde_502(client, auth, bucket, monkeypatch):
    _producto(client, auth)

    def caido(*_):
        raise httpx.ConnectError("Storage caído")

    monkeypatch.setattr(storage, "subir", caido)
    assert _subir(client, auth).status_code == 502
    assert client.get("/admin/productos/1", headers=auth).json()["imagenes"] == []


def test_cambiar_la_principal(client, auth, bucket):
    _producto(client, auth)
    _subir(client, auth)
    segunda = _subir(client, auth).json()["id"]
    imagenes = client.patch(f"{URL}/{segunda}/principal", headers=auth).json()
    assert [(i["id"], i["es_principal"]) for i in imagenes] == [(1, False), (2, True)]


def test_eliminar_la_principal_promueve_la_siguiente(client, auth, bucket):
    _producto(client, auth)
    primera = _subir(client, auth).json()["id"]
    _subir(client, auth)
    assert client.delete(f"{URL}/{primera}", headers=auth).status_code == 204
    restantes = client.get("/admin/productos/1", headers=auth).json()["imagenes"]
    assert [(i["id"], i["es_principal"]) for i in restantes] == [(2, True)]
    assert len(bucket) == 1  # el archivo también se borró del bucket


def test_imagen_de_otro_producto(client, auth, bucket):
    _producto(client, auth)
    client.post("/admin/productos", json={**COLLAR, "nombre": "Otro collar"}, headers=auth)
    ajena = client.post("/admin/productos/2/imagenes", files={"foto": ("a.jpg", JPG, "image/jpeg")},
                        headers=auth).json()["id"]
    assert client.delete(f"{URL}/{ajena}", headers=auth).status_code == 404
    assert client.patch(f"{URL}/{ajena}/principal", headers=auth).status_code == 404


def test_con_foto_ya_se_puede_exigir_al_publicar(client, auth, bucket, monkeypatch):
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", True)
    _producto(client, auth)
    assert client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth).status_code == 409
    _subir(client, auth)
    assert client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth).status_code == 200


def test_la_imagen_generica_no_cuenta_como_foto_para_publicar(client, auth, bucket, monkeypatch):
    """foto_principal nunca es null, pero la genérica no engaña a PUBLICAR_EXIGE_FOTO."""
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", True)
    _producto(client, auth)
    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert (fila["foto_principal"], fila["foto_generica"]) == (config.FOTO_GENERICA_URL, True)
    assert client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth).status_code == 409
    real = _subir(client, auth).json()["url"]
    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert (fila["foto_principal"], fila["foto_generica"]) == (real, False)


def test_al_borrar_la_ultima_foto_vuelve_la_generica(client, auth, bucket):
    _producto(client, auth)
    foto = _subir(client, auth).json()["id"]
    client.delete(f"{URL}/{foto}", headers=auth)
    assert client.get("/admin/productos", headers=auth).json()[0]["foto_generica"] is True
