"""HU033 (AKASH-115): el comprobante de la compra va a un bucket privado de Supabase.
Supabase esta simulado: estas pruebas no suben ni piden nada a Storage."""
import httpx
import pytest

from app.services import storage

ROLL_ON = {
    "categoria_id": 5,
    "nombre": "Roll-on de cuarzo",
    "descripcion": "Roll-on de aceite esencial con chips de cuarzo natural.",
    "precio_base": "30.00",
}
COMPRA = {
    "proveedor": "Minerales del Sur",
    "proveedor_ruc": "20512345678",
    "tipo_comprobante": "factura",
    "numero_comprobante": "F001-000123",
    "fecha": "2026-10-14",
    "items": [{"variante_id": 1, "cantidad": 10, "costo_unitario": "12.50"}],
}
PDF = b"%PDF-1.4\n" + b"0" * 200
JPG = b"\xff\xd8\xff\xe0" + b"0" * 200
RUTA = "/admin/compras/1/comprobante"


@pytest.fixture
def compra(client, auth):
    """Una compra registrada (id 1) que todavia no tiene comprobante."""
    client.post("/admin/productos", json=ROLL_ON, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista"}, headers=auth)
    assert client.post("/admin/compras", json=COMPRA, headers=auth).status_code == 201


@pytest.fixture
def storage_falso(monkeypatch):
    registro = {"subidos": [], "borrados": []}

    def subir(ruta, contenido, content_type):
        registro["subidos"].append((ruta, content_type))
        return ruta

    def borrar(ruta):
        registro["borrados"].append(ruta)

    monkeypatch.setattr(storage, "subir_privado", subir)
    monkeypatch.setattr(storage, "borrar_privado", borrar)
    monkeypatch.setattr(storage, "url_firmada", lambda ruta, segundos=300: f"https://supabase.test/firmado/{ruta}?token=abc")
    return registro


def _subir(client, auth, contenido=PDF, nombre="comprobante.pdf", tipo="application/pdf", ruta=RUTA):
    return client.post(ruta, files={"archivo": (nombre, contenido, tipo)}, headers=auth)


def test_exige_token(client):
    assert client.post(RUTA, files={"archivo": ("a.pdf", PDF, "application/pdf")}).status_code == 401
    assert client.get(RUTA).status_code == 401


def test_subir_pdf(client, auth, compra, storage_falso):
    respuesta = _subir(client, auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["tiene_comprobante"] is True
    ruta, tipo = storage_falso["subidos"][0]
    assert tipo == "application/pdf"
    assert ruta.startswith("compras/1/") and ruta.endswith(".pdf")


def test_subir_foto_jpg(client, auth, compra, storage_falso):
    respuesta = _subir(client, auth, JPG, "foto.jpg", "image/jpeg")
    assert respuesta.status_code == 200
    assert storage_falso["subidos"][0][0].endswith(".jpg")


def test_rechaza_archivo_que_no_es_foto_ni_pdf(client, auth, compra, storage_falso):
    respuesta = _subir(client, auth, b"MZ" + b"0" * 200, "virus.pdf", "application/pdf")  # dice ser PDF pero no lo es
    assert respuesta.status_code == 415
    assert storage_falso["subidos"] == []


def test_rechaza_mas_de_5_mb(client, auth, compra, storage_falso):
    respuesta = _subir(client, auth, b"%PDF-" + b"0" * (5 * 1024 * 1024))
    assert respuesta.status_code == 413
    assert storage_falso["subidos"] == []


def test_compra_inexistente(client, auth, compra, storage_falso):
    assert _subir(client, auth, ruta="/admin/compras/999/comprobante").status_code == 404
    assert client.get("/admin/compras/999/comprobante", headers=auth).status_code == 404


def test_ver_comprobante_da_enlace_temporal(client, auth, compra, storage_falso):
    _subir(client, auth)
    respuesta = client.get(RUTA, headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["url"].startswith("https://supabase.test/firmado/compras/1/")
    assert respuesta.json()["expira_en_segundos"] == 300


def test_ver_sin_comprobante_da_404(client, auth, compra, storage_falso):
    assert client.get(RUTA, headers=auth).status_code == 404


def test_reemplazar_borra_el_comprobante_anterior(client, auth, compra, storage_falso):
    _subir(client, auth)
    primero = storage_falso["subidos"][0][0]
    _subir(client, auth, JPG, "foto.jpg", "image/jpeg")
    assert storage_falso["borrados"] == [primero]


def test_si_falla_supabase_no_queda_marcado(client, auth, compra, storage_falso, monkeypatch):
    def caido(ruta, contenido, content_type):
        raise httpx.ConnectError("sin conexion")

    monkeypatch.setattr(storage, "subir_privado", caido)
    assert _subir(client, auth).status_code == 502
    assert client.get("/admin/compras/1", headers=auth).json()["tiene_comprobante"] is False