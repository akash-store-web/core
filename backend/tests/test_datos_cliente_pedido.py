"""HU035 (AKASH-209): nombre completo y dirección obligatorios al enviar el pedido; solo delivery.

Los datos son ficticios: nunca usar datos de clientas reales."""
import pytest

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
    """Anillo publicado (variante 1, S/ 40, 5 u.) y distrito 1 Miraflores con envío de S/ 10."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    dar_stock(client, auth, 1, 5)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    zona = client.post("/admin/zonas-envio", json={"nombre": "Lima", "costo": "10.00"}, headers=auth).json()
    client.post("/admin/distritos", json={"nombre": "Miraflores", "zona_envio_id": zona["id"]}, headers=auth)


def _pedido(**cambios):
    datos = {"nombres": "Ana María", "apellido_paterno": "Quispe", "apellido_materno": "Mamani",
             "celular": "911111111", "distrito_id": 1, "direccion": "Av. Ficticia 123, dpto. 4",
             "items": [{"variante_id": 1, "cantidad": 1}]}
    datos.update(cambios)
    return datos


def _sin_pedidos(client, auth):
    return client.get("/admin/pedidos", headers=auth).json() == []


# --- Escenario 1: datos completos ---

def test_guarda_el_nombre_completo_y_la_direccion(client, auth, tienda):
    respuesta = client.post(URL, json=_pedido())
    assert respuesta.status_code == 201, respuesta.text
    pedido = respuesta.json()
    assert (pedido["nombre"], pedido["direccion"]) == ("Ana María Quispe Mamani", "Av. Ficticia 123, dpto. 4")
    clienta = client.get("/admin/pedidos/1", headers=auth).json()["clienta"]
    assert (clienta["nombre"], clienta["direccion"]) == ("Ana María Quispe Mamani", "Av. Ficticia 123, dpto. 4")
    assert client.get("/admin/pedidos", headers=auth).json()[0]["clienta"] == "Ana María Quispe Mamani"


@pytest.mark.parametrize("nombres, paterno, materno", [
    ("María José", "De la Cruz", "Ñañez"),
    ("Ángel", "D'Angelo", "Pérez-Rojas"),
    ("Zoë", "O’Brien", "Müller"),
])
def test_acepta_tildes_enie_guion_y_apostrofo(client, tienda, nombres, paterno, materno):
    respuesta = client.post(URL, json=_pedido(nombres=nombres, apellido_paterno=paterno, apellido_materno=materno))
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["nombre"] == f"{nombres} {paterno} {materno}"


def test_limpia_espacios_sobrantes(client, tienda):
    pedido = client.post(URL, json=_pedido(nombres="  Ana   María ", apellido_paterno=" Quispe",
                                           direccion="  Av.   Ficticia 123  ")).json()
    assert (pedido["nombre"], pedido["direccion"]) == ("Ana María Quispe Mamani", "Av. Ficticia 123")


def test_no_pide_ni_guarda_dni(client, auth, tienda):
    """El DNI lo pide la propietaria por WhatsApp; si el navegador lo manda, se ignora."""
    respuesta = client.post(URL, json=_pedido(dni="12345678"))
    assert respuesta.status_code == 201
    assert "dni" not in respuesta.json()
    assert "dni" not in client.get("/admin/pedidos/1", headers=auth).json()["clienta"]


def test_el_campo_nombre_antiguo_se_ignora(client, tienda):
    """Si el formulario manda además `nombre` (ya unido), manda lo de los tres campos."""
    pedido = client.post(URL, json=_pedido(nombre="Otra Persona")).json()
    assert pedido["nombre"] == "Ana María Quispe Mamani"


# --- E2: dato faltante / E4: validación en el servidor ---

@pytest.mark.parametrize("campo", ["nombres", "apellido_paterno", "apellido_materno", "direccion"])
def test_falta_un_dato(client, auth, tienda, campo):
    datos = _pedido()
    del datos[campo]
    respuesta = client.post(URL, json=datos)
    assert respuesta.status_code == 422
    assert campo in {e["loc"][-1] for e in respuesta.json()["detail"]}  # indica el campo faltante
    assert _sin_pedidos(client, auth)


@pytest.mark.parametrize("campo", ["nombres", "apellido_paterno", "apellido_materno", "direccion"])
@pytest.mark.parametrize("valor", ["", "   ", None])
def test_dato_vacio(client, auth, tienda, campo, valor):
    assert client.post(URL, json=_pedido(**{campo: valor})).status_code == 422
    assert _sin_pedidos(client, auth)


def test_solo_el_formulario_antiguo_con_nombre_se_rechaza(client, auth, tienda):
    """E4: un pedido con solo `nombre` (sin los tres campos) no se guarda."""
    datos = _pedido(nombre="Ana Prueba")
    for campo in ("nombres", "apellido_paterno", "apellido_materno"):
        del datos[campo]
    assert client.post(URL, json=datos).status_code == 422
    assert _sin_pedidos(client, auth)


# --- E3: caracteres inválidos ---

@pytest.mark.parametrize("campo", ["nombres", "apellido_paterno", "apellido_materno"])
@pytest.mark.parametrize("valor", ["Ana2", "Ana_María", "Ana@", "<b>Ana</b>", "Ana--María", "-Ana", "Ana'",
                                   "12345", "Ana.", "😀Ana"])
def test_rechaza_numeros_y_simbolos(client, auth, tienda, campo, valor):
    respuesta = client.post(URL, json=_pedido(**{campo: valor}))
    assert respuesta.status_code == 422
    assert "solo se aceptan letras" in str(respuesta.json()["detail"])
    assert _sin_pedidos(client, auth)


# --- Largos ---

def test_nombres_y_apellidos_de_40_caracteres_se_aceptan_si_el_total_cabe(client, tienda):
    datos = _pedido(nombres="A" * 40, apellido_paterno="B" * 39, apellido_materno="C" * 39)  # 40+39+39+2 = 120
    assert client.post(URL, json=datos).status_code == 201


def test_nombre_completo_de_mas_de_120_se_rechaza(client, auth, tienda):
    datos = _pedido(nombres="A" * 40, apellido_paterno="B" * 40, apellido_materno="C" * 40)  # 122
    respuesta = client.post(URL, json=datos)
    assert respuesta.status_code == 422
    assert "120" in str(respuesta.json()["detail"])
    assert _sin_pedidos(client, auth)


@pytest.mark.parametrize("direccion, esperado", [
    ("Av 1", 422), ("Av. 1", 201), ("x" * 150, 201), ("x" * 151, 422),
])
def test_direccion_de_5_a_150_caracteres(client, tienda, direccion, esperado):
    assert client.post(URL, json=_pedido(direccion=direccion)).status_code == esperado


# --- Solo delivery (AKASH-211) ---

def test_solo_delivery(client, auth, tienda):
    assert client.post(URL, json=_pedido(modalidad_entrega="recojo")).status_code == 422
    assert _sin_pedidos(client, auth)
    pedido = client.post(URL, json=_pedido()).json()
    assert (pedido["modalidad_entrega"], pedido["costo_envio"], pedido["total"]) == ("delivery", "10.00", "50.00")
