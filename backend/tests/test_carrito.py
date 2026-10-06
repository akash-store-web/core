"""HU009: validar el carrito contra la disponibilidad (pruebas HU009 #6)."""
import pytest

from app.services import carrito as servicio_carrito

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
    "es_pieza_natural": True,
    "existencias": 3,
}
URL = "/carrito/validar"


@pytest.fixture
def anillo(client, auth):
    """Anillo publicado: variante 1 Amatista (S/ 45, 3 unidades) y variante 2 Turmalina (S/ 40, 2 unidades)."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "45.00", "existencias": 3}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Turmalina negra", "existencias": 2}, headers=auth)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)


def _validar(client, *items):
    return client.post(URL, json={"items": [{"variante_id": v, "cantidad": c} for v, c in items]})


def test_es_publico_y_valida_un_pedido_correcto(client, anillo):
    respuesta = _validar(client, (1, 2), (2, 1))
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is True
    assert cuerpo["total"] == "130.00"  # 2 × 45 + 1 × 40
    amatista = cuerpo["items"][0]
    assert amatista == {
        "variante_id": 1, "producto_id": 1, "producto": "Anillo de plata 925 con piedra", "variante": "Amatista",
        "es_pieza_natural": True, "cantidad": 2, "estado": "ok", "cantidad_maxima": 3,
        "precio_unitario": "45.00", "subtotal": "90.00", "mensaje": None,
    }


def test_cantidad_mayor_al_stock(client, anillo):
    cuerpo = _validar(client, (2, 5)).json()
    item = cuerpo["items"][0]
    assert cuerpo["valido"] is False
    assert (item["estado"], item["cantidad_maxima"]) == ("stock_insuficiente", 2)
    assert item["mensaje"] == "Solo quedan 2; ajusta la cantidad"
    assert item["subtotal"] == "80.00"  # se calcula con lo que sí se puede comprar
    assert cuerpo["total"] == "80.00"


def test_justo_el_stock_disponible_es_valido(client, anillo):
    assert _validar(client, (2, 2)).json()["valido"] is True


def test_variante_agotada(client, auth, anillo):
    client.patch("/admin/variantes/2/stock", json={"existencias": 0}, headers=auth)
    cuerpo = _validar(client, (1, 1), (2, 1)).json()
    assert cuerpo["valido"] is False
    assert [i["estado"] for i in cuerpo["items"]] == ["ok", "agotado"]
    assert cuerpo["items"][1]["cantidad_maxima"] == 0
    assert cuerpo["total"] == "45.00"


def test_producto_despublicado_o_variante_inexistente(client, auth, anillo):
    client.patch("/admin/productos/1/publicado", json={"publicado": False}, headers=auth)
    cuerpo = _validar(client, (1, 1), (99, 1)).json()
    assert cuerpo["valido"] is False
    assert [i["estado"] for i in cuerpo["items"]] == ["no_disponible", "no_disponible"]
    assert cuerpo["items"][1]["producto"] is None
    assert cuerpo["total"] == "0.00"


def test_misma_variante_repetida_se_suma(client, anillo):
    cuerpo = _validar(client, (2, 1), (2, 2)).json()
    assert len(cuerpo["items"]) == 1
    assert (cuerpo["items"][0]["cantidad"], cuerpo["items"][0]["estado"]) == (3, "stock_insuficiente")


def test_usa_el_precio_vigente(client, auth, anillo):
    client.put("/admin/productos/1", json={**{k: v for k, v in ANILLO.items() if k != "existencias"}, "precio_base": "38.00"},
               headers=auth)
    turmalina = _validar(client, (2, 1)).json()["items"][0]
    assert turmalina["precio_unitario"] == "38.00"  # hereda el nuevo precio base


def test_resta_las_unidades_reservadas(client, anillo, monkeypatch):
    """Cuando existan pedidos pendientes (HU010/HU011), sus reservas reducen lo disponible."""
    monkeypatch.setattr(servicio_carrito, "unidades_reservadas", lambda db, ids: {1: 2})
    item = _validar(client, (1, 2)).json()["items"][0]
    assert (item["estado"], item["cantidad_maxima"]) == ("stock_insuficiente", 1)


def test_cantidades_invalidas(client, anillo):
    assert _validar(client, (1, 0)).status_code == 422
    assert _validar(client, (1, -1)).status_code == 422
    assert _validar(client, (1, 100)).status_code == 422
    assert client.post(URL, json={"items": []}).status_code == 422
    assert client.post(URL, json={}).status_code == 422
