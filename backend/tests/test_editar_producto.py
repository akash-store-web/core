"""HU032: editar un producto registrado (pruebas AKASH-111), un bloque por escenario de aceptación."""
import pytest

from app import config
from app.services import storage

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
COLLAR = {
    "categoria_id": 3,
    "nombre": "Collar de amatista",
    "descripcion": "Collar con dije de amatista natural.",
    "precio_base": "35.00",
    "material": "Acero quirúrgico",
    "medidas": "Cadena de 45 cm",
    "es_pieza_natural": True,
}
EDITABLES = {k: v for k, v in COLLAR.items()}


@pytest.fixture
def collar(client, auth):
    """Collar publicado con dos variantes: Amatista (4 u.) y Cuarzo rosa (2 u.)."""
    client.post("/admin/productos", json={**COLLAR, "existencias": 4}, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Cuarzo rosa", "existencias": 2}, headers=auth)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    return 1


@pytest.fixture
def bucket(monkeypatch):
    archivos = {}
    monkeypatch.setattr(config, "SUPABASE_URL", "https://prueba.supabase.co")

    def subir(ruta, contenido, content_type):
        archivos[ruta] = contenido
        return storage.url_publica(ruta)

    monkeypatch.setattr(storage, "subir", subir)
    monkeypatch.setattr(storage, "borrar", lambda ruta: archivos.pop(ruta))
    return archivos


def _editar(client, auth, **cambios):
    return client.put("/admin/productos/1", json={**EDITABLES, **cambios}, headers=auth)


# --- Escenario 1: edición de datos ---

def test_editar_datos_se_refleja_en_el_panel_y_en_el_catalogo(client, auth, collar):
    respuesta = _editar(client, auth, nombre="Collar de amatista natural", precio_base="38.00",
                        descripcion="Nueva descripción.", categoria_id=7)
    assert respuesta.status_code == 200

    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert (fila["nombre"], fila["precio_base"], fila["categoria"]) == (
        "Collar de amatista natural", "38.00", "Decoración y amuletos")

    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["nombre"], tarjeta["precio"], tarjeta["categoria_id"]) == ("Collar de amatista natural", "38.00", 7)
    assert client.get("/catalogo/1").json()["descripcion"] == "Nueva descripción."


def test_editar_no_cambia_publicado_ni_variantes(client, auth, collar):
    _editar(client, auth, precio_base="40.00")
    assert client.get("/admin/productos/1", headers=auth).json()["publicado"] is True
    assert [v["nombre"] for v in client.get("/admin/productos/1/variantes", headers=auth).json()] == ["Amatista", "Cuarzo rosa"]


# --- Escenario 2: fotos y variantes ---

def test_agregar_y_quitar_fotos(client, auth, collar, bucket):
    primera = client.post("/admin/productos/1/imagenes", files={"foto": ("a.jpg", JPG, "image/jpeg")}, headers=auth).json()
    segunda = client.post("/admin/productos/1/imagenes", files={"foto": ("b.jpg", JPG, "image/jpeg")}, headers=auth).json()
    assert client.delete(f"/admin/productos/1/imagenes/{primera['id']}", headers=auth).status_code == 204
    imagenes = client.get("/admin/productos/1", headers=auth).json()["imagenes"]
    assert [(i["id"], i["es_principal"]) for i in imagenes] == [(segunda["id"], True)]


def test_agregar_y_renombrar_variantes_sin_perder_las_otras(client, auth, collar):
    client.post("/admin/productos/1/variantes", json={"nombre": "Ojo de tigre"}, headers=auth)
    client.put("/admin/productos/1/variantes/2", json={"nombre": "Cuarzo rosa claro", "precio": "39.00"}, headers=auth)
    variantes = client.get("/admin/productos/1/variantes", headers=auth).json()
    assert [(v["nombre"], v["precio_efectivo"], v["existencias"]) for v in variantes] == [
        ("Amatista", "35.00", 4), ("Cuarzo rosa claro", "39.00", 2), ("Ojo de tigre", "35.00", 0)]


# --- Escenario 3: validaciones ---

@pytest.mark.parametrize("campo, valor", [
    ("nombre", "   "),
    ("descripcion", ""),
    ("precio_base", "0"),
    ("precio_base", "-5"),
    ("precio_base", "12.345"),
    ("precio_base", "abc"),
])
def test_validaciones_indican_el_campo(client, auth, collar, campo, valor):
    respuesta = _editar(client, auth, **{campo: valor})
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][-1] == campo  # el frontend sabe qué campo marcar


def test_campo_obligatorio_ausente_y_categoria_inexistente(client, auth, collar):
    datos = {k: v for k, v in EDITABLES.items() if k != "precio_base"}
    assert client.put("/admin/productos/1", json=datos, headers=auth).status_code == 422
    assert _editar(client, auth, categoria_id=99).status_code == 422
    assert client.get("/admin/productos/1", headers=auth).json()["precio_base"] == "35.00"  # nada cambió


def test_validaciones_de_variante(client, auth, collar):
    assert client.put("/admin/productos/1/variantes/1", json={"nombre": ""}, headers=auth).status_code == 422
    assert client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "0"}, headers=auth).status_code == 422


def test_editar_producto_o_variante_inexistente(client, auth, collar):
    assert client.put("/admin/productos/99", json=EDITABLES, headers=auth).status_code == 404
    assert client.put("/admin/productos/1/variantes/99", json={"nombre": "X"}, headers=auth).status_code == 404


# --- Escenario 4: existencias no editables ---

def test_las_existencias_no_se_editan_desde_la_variante(client, auth, collar):
    respuesta = client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "existencias": 99}, headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["existencias"] == 4


def test_las_existencias_no_se_editan_desde_el_producto(client, auth, collar):
    _editar(client, auth, existencias=99)
    assert client.get("/admin/productos", headers=auth).json()[0]["existencias_total"] == 6


def test_editar_exige_token(client, collar):
    assert client.put("/admin/productos/1", json=EDITABLES).status_code == 401
    assert client.put("/admin/productos/1/variantes/1", json={"nombre": "X"}).status_code == 401
