"""Catálogo público: solo publicados (HU016), precio visible (HU002) y agotados (HU003, HU015)."""
from sqlalchemy.orm import Session

from app import config
from app.models.imagen import Imagen
from tests.fabricas import dar_stock

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
    "material": "Plata 925",
    "medidas": "Piedra de 8 × 10 mm",
    "es_pieza_natural": True,
}
SPRAY = {
    "categoria_id": 6,
    "nombre": "Spray áurico",
    "descripcion": "Spray de 60 ml con agua floral y aceites esenciales.",
    "precio_base": "25.00",
}


def _crear(client, auth, datos, publicar=True, stock=2):
    pid = client.post("/admin/productos", json=datos, headers=auth).json()["id"]
    if stock:
        unica = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
        dar_stock(client, auth, unica, stock)
    if publicar:
        assert client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth).status_code == 200
    return pid


def _anillo_con_dos_precios(client, auth):
    """Caso real: S/ 45 en amatista y S/ 40 en turmalina."""
    pid = _crear(client, auth, ANILLO, publicar=False, stock=3)
    unica = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
    client.put(f"/admin/productos/{pid}/variantes/{unica}", json={"nombre": "Amatista", "precio": "45.00"}, headers=auth)
    turmalina = client.post(f"/admin/productos/{pid}/variantes", json={"nombre": "Turmalina negra"}, headers=auth).json()
    dar_stock(client, auth, turmalina["id"], 2)
    client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth)
    return pid


def test_catalogo_no_exige_login(client):
    assert client.get("/catalogo").status_code == 200
    assert client.get("/catalogo/categorias").status_code == 200


def test_solo_muestra_publicados(client, auth):
    _crear(client, auth, SPRAY)
    _crear(client, auth, {**SPRAY, "nombre": "Spray en borrador"}, publicar=False)
    assert [p["nombre"] for p in client.get("/catalogo").json()] == ["Spray áurico"]


def test_despublicar_lo_oculta_al_instante(client, auth):
    pid = _crear(client, auth, SPRAY)
    client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": False}, headers=auth)
    assert client.get("/catalogo").json() == []
    assert client.get(f"/catalogo/{pid}").status_code == 404


def test_tarjeta_con_precio_unico(client, auth):
    _crear(client, auth, SPRAY)
    tarjeta = client.get("/catalogo").json()[0]
    assert tarjeta == {
        "id": 1, "nombre": "Spray áurico", "categoria_id": 6, "categoria": "Inciensos y limpieza energética",
        "precio": "25.00", "precio_desde": False, "disponible": True, "es_pieza_natural": False,
        "foto_principal": config.FOTO_GENERICA_URL, "foto_generica": True,
    }


def test_precio_desde_con_variantes_de_distinto_precio(client, auth):
    _anillo_con_dos_precios(client, auth)
    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["precio"], tarjeta["precio_desde"]) == ("40.00", True)


def test_agotado_cuando_todas_las_variantes_llegan_a_cero(client, auth):
    pid = _crear(client, auth, SPRAY)
    variante = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
    dar_stock(client, auth, variante, -2, "Se agotó")
    assert client.get("/catalogo").json()[0]["disponible"] is False  # se sigue mostrando, como "Agotado"


def test_ficha_con_variantes_y_una_agotada(client, auth):
    pid = _anillo_con_dos_precios(client, auth)
    turmalina = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[1]["id"]
    dar_stock(client, auth, turmalina, -2, "Se agotó")

    ficha = client.get(f"/catalogo/{pid}").json()
    assert ficha["tiene_variantes"] is True
    assert ficha["disponible"] is True
    assert [(v["nombre"], v["precio"], v["disponible"]) for v in ficha["variantes"]] == [
        ("Amatista", "45.00", True),
        ("Turmalina negra", "40.00", False),
    ]
    assert ficha["material"] == "Plata 925"
    assert "existencias" not in ficha["variantes"][0]  # la cantidad exacta no es pública


def test_ficha_sin_variantes_oculta_el_selector(client, auth):
    pid = _crear(client, auth, SPRAY)
    ficha = client.get(f"/catalogo/{pid}").json()
    assert ficha["tiene_variantes"] is False
    assert [v["nombre"] for v in ficha["variantes"]] == ["Única"]


def test_foto_principal_e_imagenes(client, auth, engine):
    pid = _crear(client, auth, SPRAY)
    with Session(engine) as db:
        db.add_all([Imagen(producto_id=pid, url="https://ejemplo/2.jpg", orden=1),
                    Imagen(producto_id=pid, url="https://ejemplo/1.jpg", orden=0, es_principal=True)])
        db.commit()
    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["foto_principal"], tarjeta["foto_generica"]) == ("https://ejemplo/1.jpg", False)
    assert [i["url"] for i in client.get(f"/catalogo/{pid}").json()["imagenes"]] == ["https://ejemplo/1.jpg",
                                                                                      "https://ejemplo/2.jpg"]


def test_filtros_y_orden_por_categoria(client, auth):
    _crear(client, auth, SPRAY)
    _anillo_con_dos_precios(client, auth)
    assert [p["nombre"] for p in client.get("/catalogo").json()] == ["Anillo de plata 925 con piedra", "Spray áurico"]
    assert [p["nombre"] for p in client.get("/catalogo", params={"categoria_id": 6}).json()] == ["Spray áurico"]
    assert [p["nombre"] for p in client.get("/catalogo", params={"q": "ANILLO"}).json()] == [
        "Anillo de plata 925 con piedra"]


def test_categorias_solo_con_productos_publicados(client, auth):
    _crear(client, auth, SPRAY)
    _crear(client, auth, ANILLO, publicar=False)
    assert client.get("/catalogo/categorias").json() == [{"id": 6, "nombre": "Inciensos y limpieza energética"}]


def test_ficha_inexistente(client):
    assert client.get("/catalogo/99").status_code == 404


def test_solo_disponibles_oculta_los_agotados(client, auth):
    """HU029: el interruptor «Ver solo disponibles»."""
    spray = _crear(client, auth, SPRAY)
    _anillo_con_dos_precios(client, auth)
    variante = client.get(f"/admin/productos/{spray}/variantes", headers=auth).json()[0]["id"]
    dar_stock(client, auth, variante, -2, "Se agotó")

    todos = [p["nombre"] for p in client.get("/catalogo").json()]
    disponibles = [p["nombre"] for p in client.get("/catalogo", params={"solo_disponibles": True}).json()]
    assert todos == ["Anillo de plata 925 con piedra", "Spray áurico"]
    assert disponibles == ["Anillo de plata 925 con piedra"]


def test_solo_disponibles_se_combina_con_los_otros_filtros(client, auth):
    _crear(client, auth, SPRAY)
    _anillo_con_dos_precios(client, auth)
    filtrado = client.get("/catalogo", params={"solo_disponibles": True, "categoria_id": 6}).json()
    assert [p["nombre"] for p in filtrado] == ["Spray áurico"]
    assert client.get("/catalogo", params={"solo_disponibles": "talvez"}).status_code == 422
