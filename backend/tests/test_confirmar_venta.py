"""HU018: confirmar la venta y gestionar el estado del pedido (AKASH-202).

Los datos de clientas son ficticios: nunca usar datos de clientas reales."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.pedido import EstadoPedido
from app.services import pedidos as servicio_pedidos
from tests.fabricas import crear_pedido, dar_stock

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
}


@pytest.fixture
def tienda(client, auth):
    """Anillo publicado: variante 1 Amatista (S/ 45, 3 u.) y 2 Turmalina (S/ 40, 2 u.)."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "45.00"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Turmalina negra"}, headers=auth)
    dar_stock(client, auth, 1, 3)
    dar_stock(client, auth, 2, 2)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)


@pytest.fixture
def pedido(engine, tienda):
    """P-0001 pendiente: 2 Amatista + 1 Turmalina."""
    with Session(engine) as db:
        return crear_pedido(db, "P-0001", [(1, 2, "45.00"), (2, 1, "40.00")]).id


def _estado(client, auth, estado, pedido_id=1):
    return client.patch(f"/admin/pedidos/{pedido_id}/estado", json={"estado": estado}, headers=auth)


def _existencias(client, auth):
    return {v["id"]: v["existencias"] for v in client.get("/admin/productos/1/variantes", headers=auth).json()}


def _ventas(client, auth, variante_id):
    return [m for m in client.get(f"/admin/variantes/{variante_id}/movimientos", headers=auth).json()
            if m["tipo"] == "venta"]


# --- Acceso y validaciones ---

def test_exige_token(client, pedido):
    assert client.patch("/admin/pedidos/1/estado", json={"estado": "confirmado"}).status_code == 401


def test_pedido_inexistente(client, auth, pedido):
    assert _estado(client, auth, "confirmado", pedido_id=99).status_code == 404


@pytest.mark.parametrize("estado", ["pendiente", "inventado", "", None])
def test_estado_no_valido(client, auth, pedido, estado):
    assert _estado(client, auth, estado).status_code == 422


# --- Escenario 1: confirmar descuenta el stock ---

def test_confirmar_descuenta_stock_y_registra_venta(client, auth, pedido):
    respuesta = _estado(client, auth, "confirmado")
    assert respuesta.status_code == 200, respuesta.text
    detalle = respuesta.json()
    assert detalle["estado"] == "confirmado"
    assert detalle["numero"] == "P-0001"
    assert [(h["estado"], h["usuario"]) for h in detalle["historial"]] == [
        ("pendiente", None), ("confirmado", "duena@example.com")]
    assert _existencias(client, auth) == {1: 1, 2: 1}
    venta = _ventas(client, auth, 1)
    assert [(m["cantidad"], m["saldo"], m["pedido_numero"], m["usuario"]) for m in venta] == [
        (-2, 1, "P-0001", "duena@example.com")]
    assert [m["cantidad"] for m in _ventas(client, auth, 2)] == [-1]


# --- Escenario 2: cancelar un pendiente ---

def test_cancelar_pendiente_no_cambia_stock(client, auth, pedido):
    respuesta = _estado(client, auth, "cancelado")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelado"
    assert [h["estado"] for h in respuesta.json()["historial"]] == ["pendiente", "cancelado"]
    assert _existencias(client, auth) == {1: 3, 2: 2}
    assert _ventas(client, auth, 1) == []


# --- Escenario 3: enviado y entregado ---

def test_enviado_y_entregado_con_fecha_y_usuario(client, auth, pedido):
    _estado(client, auth, "confirmado")
    assert _estado(client, auth, "enviado").json()["estado"] == "enviado"
    detalle = _estado(client, auth, "entregado").json()
    assert detalle["estado"] == "entregado"
    historial = detalle["historial"]
    assert [h["estado"] for h in historial] == ["pendiente", "confirmado", "enviado", "entregado"]
    assert all(h["fecha"] and h["usuario"] == "duena@example.com" for h in historial[1:])
    assert _existencias(client, auth) == {1: 1, 2: 1}  # solo confirmar mueve el stock


def test_bandeja_filtra_por_los_estados_nuevos(client, auth, pedido, engine):
    with Session(engine) as db:
        crear_pedido(db, "P-0002", [(2, 1, "40.00")], telefono="922222222")
    _estado(client, auth, "confirmado")
    _estado(client, auth, "enviado")
    _estado(client, auth, "cancelado", pedido_id=2)
    for estado, esperados in [("enviado", ["P-0001"]), ("cancelado", ["P-0002"]), ("pendiente", []),
                              ("confirmado", [])]:
        bandeja = client.get("/admin/pedidos", params={"estado": estado}, headers=auth).json()
        assert [p["numero"] for p in bandeja] == esperados


# --- E4: stock insuficiente ---

def test_stock_insuficiente_no_cambia_nada(client, auth, engine, tienda):
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(1, 5, "45.00"), (2, 1, "40.00")])
    respuesta = _estado(client, auth, "confirmado")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "mensaje": "No hay stock suficiente para confirmar el pedido P-0001",
        "items": [{"variante_id": 1, "producto": "Anillo de plata 925 con piedra", "variante": "Amatista",
                   "solicitada": 5, "disponible": 3}],
    }
    assert client.get("/admin/pedidos/1", headers=auth).json()["estado"] == "pendiente"
    assert _existencias(client, auth) == {1: 3, 2: 2}  # tampoco se descontó la Turmalina, que sí alcanzaba
    assert _ventas(client, auth, 2) == []


def test_lineas_repetidas_de_una_variante_se_suman(client, auth, engine, tienda):
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(1, 2, "45.00"), (1, 2, "45.00")])
    respuesta = _estado(client, auth, "confirmado")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["items"][0]["solicitada"] == 4
    assert _existencias(client, auth)[1] == 3


def test_si_falla_un_movimiento_no_queda_nada_a_medias(client, auth, pedido, monkeypatch):
    """Red de seguridad: si el stock cambia entre la revisión y el descuento (carrera), rollback total."""
    original = servicio_pedidos.registrar_movimiento
    llamadas = []

    def falla_en_la_segunda(*args, **kwargs):
        llamadas.append(args)
        if len(llamadas) == 2:
            raise HTTPException(409, "Las existencias no pueden quedar en negativo")
        return original(*args, **kwargs)

    monkeypatch.setattr(servicio_pedidos, "registrar_movimiento", falla_en_la_segunda)
    assert _estado(client, auth, "confirmado").status_code == 409
    monkeypatch.undo()
    assert client.get("/admin/pedidos/1", headers=auth).json()["estado"] == "pendiente"
    assert _existencias(client, auth) == {1: 3, 2: 2}
    assert _ventas(client, auth, 1) == []


# --- E5: doble confirmación ---

def test_confirmar_dos_veces_descuenta_una_sola_vez(client, auth, pedido):
    assert _estado(client, auth, "confirmado").status_code == 200
    segunda = _estado(client, auth, "confirmado")
    assert segunda.status_code == 409
    assert segunda.json()["detail"] == "El pedido P-0001 ya está confirmado"
    assert _existencias(client, auth) == {1: 1, 2: 1}
    assert len(_ventas(client, auth, 1)) == 1


# --- E6: transiciones no permitidas ---

@pytest.mark.parametrize("camino, siguiente, mensaje", [
    (["confirmado", "enviado", "entregado"], "cancelado", "No se puede pasar de entregado a cancelado (pedido P-0001)"),
    ([], "enviado", "No se puede pasar de pendiente a enviado (pedido P-0001)"),
    ([], "entregado", "No se puede pasar de pendiente a entregado (pedido P-0001)"),
    (["cancelado"], "confirmado", "No se puede pasar de cancelado a confirmado (pedido P-0001)"),
    (["confirmado", "enviado"], "cancelado", "No se puede pasar de enviado a cancelado (pedido P-0001)"),
    (["cancelado"], "cancelado", "El pedido P-0001 ya está cancelado"),
])
def test_transicion_no_permitida(client, auth, pedido, camino, siguiente, mensaje):
    for estado in camino:
        assert _estado(client, auth, estado).status_code == 200
    stock = _existencias(client, auth)
    respuesta = _estado(client, auth, siguiente)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == mensaje
    assert _existencias(client, auth) == stock


# --- Cancelar un confirmado (decisión de Raúl, HU019 E7): devuelve el stock ---

def test_cancelar_confirmado_devuelve_el_stock(client, auth, pedido):
    _estado(client, auth, "confirmado")
    respuesta = _estado(client, auth, "cancelado")
    assert respuesta.status_code == 200
    assert [h["estado"] for h in respuesta.json()["historial"]] == ["pendiente", "confirmado", "cancelado"]
    assert _existencias(client, auth) == {1: 3, 2: 2}
    devolucion = client.get("/admin/variantes/1/movimientos", headers=auth).json()[0]
    assert (devolucion["tipo"], devolucion["cantidad"], devolucion["saldo"], devolucion["motivo"],
            devolucion["pedido_numero"]) == ("ajuste", 2, 3, "Cancelación del pedido P-0001", "P-0001")


# --- E7: la variante que queda en 0 se ve agotada en el catálogo ---

def test_tras_confirmar_la_variante_en_cero_se_ve_agotada(client, auth, engine, tienda):
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(2, 2, "40.00")])
    assert _estado(client, auth, "confirmado").status_code == 200
    ficha = client.get("/catalogo/1").json()
    disponibles = {v["id"]: v["disponible"] for v in ficha["variantes"]}
    assert disponibles == {1: True, 2: False}
    carrito = client.post("/carrito/validar", json={"items": [{"variante_id": 2, "cantidad": 1}]}).json()
    assert carrito["valido"] is False
    assert carrito["items"][0]["estado"] == "agotado"


def test_pedido_de_la_web_se_confirma(client, auth, tienda):
    """Flujo completo: la clienta lo envía por WhatsApp (HU010) y la propietaria lo confirma."""
    zona = client.post("/admin/zonas-envio", json={"nombre": "Lima", "costo": "10.00"}, headers=auth).json()
    client.post("/admin/distritos", json={"nombre": "Miraflores", "zona_envio_id": zona["id"]}, headers=auth)
    creado = client.post("/pedidos", json={"nombres": "Ana", "apellido_paterno": "Prueba",
                                           "apellido_materno": "Ficticia", "celular": "911111111",
                                           "distrito_id": 1, "direccion": "Calle Ficticia 123",
                                           "items": [{"variante_id": 1, "cantidad": 3}]})
    assert creado.status_code == 201, creado.text
    assert _existencias(client, auth)[1] == 3  # pendiente: no descuenta
    assert _estado(client, auth, "confirmado").json()["estado"] == EstadoPedido.CONFIRMADO
    assert _existencias(client, auth)[1] == 0
