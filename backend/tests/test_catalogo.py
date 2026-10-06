"""Catálogo público: solo publicados (HU016), precio visible (HU002) y agotados (HU003, HU015)."""
from sqlalchemy.orm import Session

from app.models.imagen import Imagen

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
    "material": "Plata 925",
    "medidas": "Piedra de 8 × 10 mm",
    "es_pieza_natural": True,
    "existencias": 3,
}
SPRAY = {
    "categoria_id": 6,
    "nombre": "Spray áurico",
    "descripcion": "Spray de 60 ml con agua floral y aceites esenciales.",
    "precio_base": "25.00",
    "existencias": 2,
}


def _crear(client, auth, datos, publicar=True):
    pid = client.post("/admin/productos", json=datos, headers=auth).json()["id"]
    if publicar:
        assert client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth).status_code == 200
    return pid


def _anillo_con_dos_precios(client, auth):
    """Caso real: S/ 45 en amatista y S/ 40 en turmalina."""
    pid = _crear(client, auth, ANILLO, publicar=False)
    unica = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
    client.put(f"/admin/productos/{pid}/variantes/{unica}",
               json={"nombre": "Amatista", "precio": "45.00", "existencias": 3}, headers=auth)
    client.post(f"/admin/productos/{pid}/variantes", json={"nombre": "Turmalina negra", "existencias": 2}, headers=auth)
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
        "foto_principal": None,
    }


def test_precio_desde_con_variantes_de_distinto_precio(client, auth):
    _anillo_con_dos_precios(client, auth)
    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["precio"], tarjeta["precio_desde"]) == ("40.00", True)


def test_agotado_cuando_todas_las_variantes_llegan_a_cero(client, auth):
    pid = _crear(client, auth, SPRAY)
    variante = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
    client.patch(f"/admin/variantes/{variante}/stock", json={"existencias": 0}, headers=auth)
    assert client.get("/catalogo").json()[0]["disponible"] is False  # se sigue mostrando, como "Agotado"


def test_ficha_con_variantes_y_una_agotada(client, auth):
    pid = _anillo_con_dos_precios(client, auth)
    turmalina = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[1]["id"]
    client.patch(f"/admin/variantes/{turmalina}/stock", json={"cambio": -2}, headers=auth)

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
    assert client.get("/catalogo").json()[0]["foto_principal"] == "https://ejemplo/1.jpg"
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
