"""HU010: enviar mi pedido por WhatsApp (AKASH-83 y pruebas AKASH-84).

Los datos de clientas son ficticios: nunca usar datos de clientas reales."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.pedido import Pedido
from tests.fabricas import dar_stock

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
}
URL = "/pedidos"


@pytest.fixture
def tienda(client, auth):
    """Anillo publicado: variante 1 Amatista (S/ 45, 3 u.) y 2 Turmalina (S/ 40, 2 u.).
    Distritos: 1 Miraflores (zona Lima, S/ 10), 2 Chosica (sin zona)."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "45.00"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Turmalina negra"}, headers=auth)
    dar_stock(client, auth, 1, 3)
    dar_stock(client, auth, 2, 2)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    zona = client.post("/admin/zonas-envio", json={"nombre": "Lima", "costo": "10.00"}, headers=auth).json()
    client.post("/admin/distritos", json={"nombre": "Miraflores", "zona_envio_id": zona["id"]}, headers=auth)
    client.post("/admin/distritos", json={"nombre": "Chosica"}, headers=auth)


def _pedido(**cambios):
    datos = {"nombre": "Ana Prueba", "celular": "911111111", "distrito_id": 1, "modalidad_entrega": "delivery",
             "direccion": "Calle Ficticia 123", "items": [{"variante_id": 1, "cantidad": 2},
                                                          {"variante_id": 2, "cantidad": 1}]}
    datos.update(cambios)
    return datos


# --- Escenarios 1 y 3 ---

def test_registra_el_pedido_pendiente_con_numero(client, auth, tienda):
    respuesta = client.post(URL, json=_pedido())
    assert respuesta.status_code == 201, respuesta.text
    pedido = respuesta.json()
    assert pedido["numero"] == "P-0001"
    assert pedido["estado"] == "pendiente"
    assert pedido["repetido"] is False
    assert (pedido["nombre"], pedido["celular"], pedido["distrito"], pedido["modalidad_entrega"]) == (
        "Ana Prueba", "911111111", "Miraflores", "delivery")
    assert [(i["producto"], i["variante"], i["cantidad"], i["precio_unitario"], i["subtotal"])
            for i in pedido["items"]] == [
        ("Anillo de plata 925 con piedra", "Amatista", 2, "45.00", "90.00"),
        ("Anillo de plata 925 con piedra", "Turmalina negra", 1, "40.00", "40.00")]
    assert (pedido["subtotal"], pedido["costo_envio"], pedido["total"]) == ("130.00", "10.00", "140.00")


def test_es_publico_y_aparece_en_la_bandeja(client, auth, tienda):
    client.post(URL, json=_pedido())
    bandeja = client.get("/admin/pedidos", headers=auth).json()
    assert [(p["numero"], p["estado"], p["metodo_pago"], p["total"]) for p in bandeja] == [
        ("P-0001", "pendiente", "whatsapp", "140.00")]
    detalle = client.get("/admin/pedidos/1", headers=auth).json()
    assert detalle["clienta"] == {"nombre": "Ana Prueba", "telefono": "911111111", "correo": None,
                                  "direccion": "Calle Ficticia 123", "referencia": None}
    assert [(h["estado"], h["usuario"]) for h in detalle["historial"]] == [("pendiente", None)]


def test_no_descuenta_ni_aparta_stock(client, auth, tienda):
    """El stock baja recién cuando la propietaria confirma la venta (HU018)."""
    client.post(URL, json=_pedido())
    movimientos = client.get("/admin/productos/1/movimientos", headers=auth).json()
    assert "venta" not in {m["tipo"] for m in movimientos}
    validacion = client.post("/carrito/validar", json={"items": [{"variante_id": 1, "cantidad": 3}]}).json()
    assert validacion["valido"] is True
    assert validacion["items"][0]["cantidad_maxima"] == 3


def test_numeros_correlativos(client, tienda):
    assert client.post(URL, json=_pedido()).json()["numero"] == "P-0001"
    assert client.post(URL, json=_pedido(celular="922222222")).json()["numero"] == "P-0002"


def test_recojo_no_cobra_envio_ni_exige_cobertura(client, tienda):
    pedido = client.post(URL, json=_pedido(modalidad_entrega="recojo", distrito_id=2)).json()
    assert (pedido["costo_envio"], pedido["total"]) == ("0.00", "130.00")


def test_misma_variante_dos_veces_se_suma(client, tienda):
    pedido = client.post(URL, json=_pedido(items=[{"variante_id": 1, "cantidad": 1},
                                                  {"variante_id": 1, "cantidad": 2}])).json()
    assert [(i["variante"], i["cantidad"]) for i in pedido["items"]] == [("Amatista", 3)]


def test_direccion_y_referencia_opcionales(client, tienda):
    respuesta = client.post(URL, json=_pedido(direccion="   ", referencia=None))
    assert respuesta.status_code == 201
    assert (respuesta.json()["direccion"], respuesta.json()["referencia"]) == (None, None)


# --- E4: datos obligatorios ---

@pytest.mark.parametrize("campo", ["nombre", "celular", "distrito_id", "modalidad_entrega", "items"])
def test_falta_un_dato_obligatorio(client, auth, tienda, campo):
    datos = _pedido()
    del datos[campo]
    assert client.post(URL, json=datos).status_code == 422
    assert client.get("/admin/pedidos", headers=auth).json() == []


@pytest.mark.parametrize("nombre", ["", " ", "A", "x" * 81])
def test_nombre_de_2_a_80_caracteres(client, tienda, nombre):
    assert client.post(URL, json=_pedido(nombre=nombre)).status_code == 422


def test_carrito_vacio(client, tienda):
    assert client.post(URL, json=_pedido(items=[])).status_code == 422


def test_modalidad_desconocida(client, tienda):
    assert client.post(URL, json=_pedido(modalidad_entrega="drone")).status_code == 422


# --- E5: celular inválido ---

@pytest.mark.parametrize("celular", ["811111111", "91111111", "9111111111", "9111a1111", "+51911111111"])
def test_celular_invalido(client, tienda, celular):
    assert client.post(URL, json=_pedido(celular=celular)).status_code == 422


# --- Distrito ---

def test_distrito_sin_cobertura_para_delivery(client, auth, tienda):
    respuesta = client.post(URL, json=_pedido(distrito_id=2))
    assert respuesta.status_code == 422
    assert "cobertura" in respuesta.json()["detail"]
    assert client.get("/admin/pedidos", headers=auth).json() == []


def test_distrito_inexistente(client, tienda):
    assert client.post(URL, json=_pedido(distrito_id=99)).status_code == 422


def test_zona_desactivada_deja_sin_cobertura(client, auth, tienda):
    client.put("/admin/zonas-envio/1", json={"nombre": "Lima", "costo": "10.00", "activa": False}, headers=auth)
    assert client.post(URL, json=_pedido()).status_code == 422


# --- E6: sin stock al enviar ---

def test_variante_agotada_no_registra_el_pedido(client, auth, tienda):
    dar_stock(client, auth, 2, -2, motivo="Vendida en feria")
    respuesta = client.post(URL, json=_pedido())
    assert respuesta.status_code == 409
    detalle = respuesta.json()["detail"]
    assert "no están disponibles" in detalle["mensaje"]
    assert [(i["variante_id"], i["estado"], i["cantidad_maxima"]) for i in detalle["items"]] == [(2, "agotado", 0)]
    assert client.get("/admin/pedidos", headers=auth).json() == []


def test_cantidad_mayor_a_la_disponible(client, tienda):
    respuesta = client.post(URL, json=_pedido(items=[{"variante_id": 1, "cantidad": 4}]))
    assert respuesta.status_code == 409
    item = respuesta.json()["detail"]["items"][0]
    assert (item["estado"], item["cantidad_maxima"], item["mensaje"]) == (
        "stock_insuficiente", 3, "Solo quedan 3; ajusta la cantidad")


def test_producto_despublicado(client, auth, tienda):
    client.patch("/admin/productos/1/publicado", json={"publicado": False}, headers=auth)
    respuesta = client.post(URL, json=_pedido())
    assert respuesta.status_code == 409
    assert {i["estado"] for i in respuesta.json()["detail"]["items"]} == {"no_disponible"}


def test_variante_inexistente(client, tienda):
    respuesta = client.post(URL, json=_pedido(items=[{"variante_id": 999, "cantidad": 1}]))
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["items"][0]["estado"] == "no_disponible"


# --- E7: carrito manipulado ---

def test_ignora_precios_y_totales_del_navegador(client, tienda):
    datos = _pedido(items=[{"variante_id": 1, "cantidad": 1, "precio_unitario": "0.01"}], total="0.01",
                    costo_envio="0.00", estado="confirmado")
    pedido = client.post(URL, json=datos).json()
    assert (pedido["items"][0]["precio_unitario"], pedido["total"], pedido["estado"]) == ("45.00", "55.00", "pendiente")


@pytest.mark.parametrize("cantidad", [0, -1, 1.5, "dos", 11])
def test_cantidad_invalida(client, tienda, cantidad):
    assert client.post(URL, json=_pedido(items=[{"variante_id": 1, "cantidad": cantidad}])).status_code == 422


def test_mas_de_10_sumando_lineas_repetidas(client, auth, tienda):
    dar_stock(client, auth, 1, 20)
    respuesta = client.post(URL, json=_pedido(items=[{"variante_id": 1, "cantidad": 6},
                                                     {"variante_id": 1, "cantidad": 5}]))
    assert respuesta.status_code == 422
    assert "WhatsApp" in respuesta.json()["detail"]


def test_usa_el_precio_vigente_si_cambio_despues_de_agregarlo(client, auth, tienda):
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "50.00"}, headers=auth)
    pedido = client.post(URL, json=_pedido(items=[{"variante_id": 1, "cantidad": 1}])).json()
    assert pedido["items"][0]["precio_unitario"] == "50.00"


# --- E9: doble envío ---

def test_doble_envio_registra_un_solo_pedido(client, auth, tienda):
    primero = client.post(URL, json=_pedido())
    segundo = client.post(URL, json=_pedido())
    assert (primero.status_code, segundo.status_code) == (201, 200)
    assert segundo.json()["numero"] == primero.json()["numero"] == "P-0001"
    assert segundo.json()["repetido"] is True
    assert len(client.get("/admin/pedidos", headers=auth).json()) == 1


def test_otro_carrito_del_mismo_celular_es_otro_pedido(client, tienda):
    client.post(URL, json=_pedido())
    otro = client.post(URL, json=_pedido(items=[{"variante_id": 1, "cantidad": 1}]))
    assert (otro.status_code, otro.json()["numero"]) == (201, "P-0002")


def test_el_mismo_pedido_pasados_2_minutos_es_nuevo(client, tienda, engine):
    client.post(URL, json=_pedido())
    with Session(engine) as db:
        db.get(Pedido, 1).fecha = datetime.now(timezone.utc) - timedelta(minutes=3)
        db.commit()
    otro = client.post(URL, json=_pedido())
    assert (otro.status_code, otro.json()["numero"]) == (201, "P-0002")
