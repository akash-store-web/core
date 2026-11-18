"""HU009: validar el carrito contra la disponibilidad (pruebas HU009 #6)."""
import pytest

from app.services import carrito as servicio_carrito
from tests.fabricas import dar_stock

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
    "es_pieza_natural": True,
}
URL = "/carrito/validar"


@pytest.fixture
def anillo(client, auth):
    """Anillo publicado: variante 1 Amatista (S/ 45, 3 unidades) y variante 2 Turmalina (S/ 40, 2 unidades)."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "45.00"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Turmalina negra"}, headers=auth)
    dar_stock(client, auth, 1, 3)
    dar_stock(client, auth, 2, 2)
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
        "precio_anterior": None, "precio_cambio": False,
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
    dar_stock(client, auth, 2, -2, "Se agotó")
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
    client.put("/admin/productos/1", json={**ANILLO, "precio_base": "38.00"},
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
    assert _validar(client, (1, 11)).status_code == 422  # HU009 E6: máximo 10 por línea
    assert _validar(client, (1, 10)).status_code == 200
    assert client.post(URL, json={"items": []}).status_code == 422
    assert client.post(URL, json={}).status_code == 422


# ---------- HU009 E6: máximo 10 unidades por producto ----------

def test_la_misma_variante_en_varias_lineas_no_pasa_de_10(client, auth, anillo):
    """No es 422: el ítem sale con estado "limite" y la cantidad que sí se puede pedir."""
    dar_stock(client, auth, 1, 20)  # Amatista: 23 unidades
    cuerpo = _validar(client, (1, 6), (1, 6)).json()
    item = cuerpo["items"][0]
    assert cuerpo["valido"] is False
    assert (item["cantidad"], item["estado"], item["cantidad_maxima"]) == (12, "limite", 10)
    assert item["mensaje"] == "Máximo 10 unidades por producto; para más, escríbenos por WhatsApp"
    assert item["subtotal"] == "450.00"  # 10 × 45


def test_limite_con_poco_stock_ofrece_lo_disponible(client, anillo):
    item = _validar(client, (1, 8), (1, 4)).json()["items"][0]
    assert (item["estado"], item["cantidad_maxima"]) == ("limite", 3)  # min(10, 3 disponibles)


def test_justo_10_en_varias_lineas_es_valido(client, auth, anillo):
    dar_stock(client, auth, 1, 20)
    assert _validar(client, (1, 5), (1, 5)).json()["valido"] is True


# ---------- HU009 E9 / E10: precio cambiado ----------

def _con_precio(client, *items):
    return client.post(URL, json={"items": [{"variante_id": v, "cantidad": c, "precio_visto": p}
                                            for v, c, p in items]}).json()


def test_aviso_de_precio_cambiado_sin_bloquear(client, auth, anillo):
    """E9: la clienta lo agregó a S/ 45.00 y ahora cuesta S/ 50.00: se avisa, pero se puede seguir."""
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "50.00"}, headers=auth)
    cuerpo = _con_precio(client, (1, 2, "45.00"))
    item = cuerpo["items"][0]
    assert cuerpo["valido"] is True
    assert (item["estado"], item["precio_cambio"], item["precio_anterior"]) == ("ok", True, "45.00")
    assert item["mensaje"] == "El precio cambió de S/ 45.00 a S/ 50.00"
    # E10: se cobra el vigente, nunca el guardado en el navegador
    assert (item["precio_unitario"], item["subtotal"], cuerpo["total"]) == ("50.00", "100.00", "100.00")


def test_mismo_precio_o_sin_precio_visto_no_avisa(client, anillo):
    for item in (_con_precio(client, (1, 1, "45"))["items"][0], _validar(client, (1, 1)).json()["items"][0]):
        assert (item["precio_cambio"], item["precio_anterior"], item["mensaje"]) == (False, None, None)


def test_precio_visto_manipulado_no_cambia_el_total(client, anillo):
    """E10: aunque el navegador diga 1.00, se calcula con el precio vigente."""
    cuerpo = _con_precio(client, (1, 1, "1.00"))
    assert cuerpo["total"] == "45.00"
    assert cuerpo["items"][0]["precio_cambio"] is True


def test_precio_cambiado_y_stock_insuficiente(client, auth, anillo):
    """El estado de stock manda en el mensaje; el cambio de precio igual se marca."""
    item = _con_precio(client, (2, 5, "35.00"))["items"][0]
    assert (item["estado"], item["precio_cambio"], item["precio_anterior"]) == ("stock_insuficiente", True, "35.00")
    assert item["mensaje"] == "Solo quedan 2; ajusta la cantidad"


def test_precio_visto_invalido_es_422(client, anillo):
    for valor in ("-1", "abc", "10000", "1.234"):
        assert client.post(URL, json={"items": [{"variante_id": 1, "cantidad": 1, "precio_visto": valor}]}
                           ).status_code == 422, valor
