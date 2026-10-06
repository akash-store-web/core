"""HU015: actualizar las existencias rápidamente."""

ROLL_ON = {
    "categoria_id": 5,
    "nombre": "Roll-on de cuarzo",
    "descripcion": "Roll-on de aceite esencial con esfera y chips de cuarzo natural.",
    "precio_base": "30.00",
    "existencias": 3,
}
URL = "/admin/productos/1/variantes/1/existencias"


def _producto(client, auth):
    assert client.post("/admin/productos", json=ROLL_ON, headers=auth).status_code == 201


def _patch(client, auth, url=URL, **datos):
    return client.patch(url, json=datos, headers=auth)


def test_exige_token(client):
    assert client.patch(URL, json={"cambio": 1}).status_code == 401


def test_sumar_y_restar_con_botones(client, auth):
    _producto(client, auth)
    assert _patch(client, auth, cambio=1).json()["existencias"] == 4
    assert _patch(client, auth, cambio=-2).json()["existencias"] == 2


def test_fijar_cantidad_exacta(client, auth):
    _producto(client, auth)
    respuesta = _patch(client, auth, existencias=12)
    assert respuesta.status_code == 200
    assert respuesta.json()["existencias"] == 12
    assert respuesta.json()["agotado"] is False


def test_llegar_a_cero_marca_agotado(client, auth):
    _producto(client, auth)
    respuesta = _patch(client, auth, cambio=-3)
    assert respuesta.json()["existencias"] == 0
    assert respuesta.json()["agotado"] is True
    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert fila["existencias_total"] == 0
    assert fila["agotado"] is True


def test_no_queda_en_negativo(client, auth):
    _producto(client, auth)
    respuesta = _patch(client, auth, cambio=-4)
    assert respuesta.status_code == 409
    assert client.get("/admin/productos/1/variantes", headers=auth).json()[0]["existencias"] == 3
    assert _patch(client, auth, existencias=-1).status_code == 422


def test_un_solo_campo_y_distinto_de_cero(client, auth):
    _producto(client, auth)
    assert _patch(client, auth).status_code == 422
    assert _patch(client, auth, cambio=1, existencias=5).status_code == 422
    assert _patch(client, auth, cambio=0).status_code == 422


def test_cada_variante_lleva_su_propio_stock(client, auth):
    """HU027 criterio 1: cada variante mantiene existencias independientes."""
    _producto(client, auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Citrino", "existencias": 2}, headers=auth)
    _patch(client, auth, cambio=-3)
    variantes = {v["nombre"]: v for v in client.get("/admin/productos/1/variantes", headers=auth).json()}
    assert variantes["Única"]["agotado"] is True
    assert variantes["Citrino"]["existencias"] == 2
    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert (fila["existencias_total"], fila["agotado"]) == (2, False)


def test_variante_o_producto_inexistente(client, auth):
    _producto(client, auth)
    assert _patch(client, auth, url="/admin/productos/1/variantes/99/existencias", cambio=1).status_code == 404
    assert _patch(client, auth, url="/admin/productos/99/variantes/1/existencias", cambio=1).status_code == 404
