"""HU017: bandeja y detalle de pedidos del panel (pruebas HU017 #4)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.distrito import Distrito
from app.models.pedido import EstadoPedido, HistorialEstadoPedido
from tests.fabricas import crear_pedido

ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
    "existencias": 3,
}
AYER = datetime.now(timezone.utc) - timedelta(days=1)


@pytest.fixture
def pedidos(client, auth, engine):
    """Dos pedidos: AK-0001 (ayer, por validar, con comprobante) y AK-0002 (hoy, pendiente de pago)."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "45.00", "existencias": 3}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Turmalina negra", "existencias": 2}, headers=auth)
    with Session(engine) as db:
        db.add(Distrito(nombre="Miraflores"))
        db.commit()
        crear_pedido(db, "AK-0001", [(1, 2, "45.00"), (2, 1, "40.00")], estado=EstadoPedido.POR_VALIDAR,
                     nombre="Ana Prueba", telefono="911111111", fecha=AYER, distrito_id=1,
                     comprobante_url="comprobantes/AK-0001.jpg")
        crear_pedido(db, "AK-0002", [(2, 1, "40.00")], nombre="Bea Prueba", telefono="922222222")


def test_exige_token(client):
    assert client.get("/admin/pedidos").status_code == 401
    assert client.get("/admin/pedidos/1").status_code == 401


def test_bandeja_del_mas_reciente_al_mas_antiguo(client, auth, pedidos):
    bandeja = client.get("/admin/pedidos", headers=auth).json()
    assert [p["numero"] for p in bandeja] == ["AK-0002", "AK-0001"]
    ana = bandeja[1]
    assert ana["clienta"] == "Ana Prueba"
    assert ana["telefono"] == "911111111"
    assert ana["total"] == "140.00"  # 2 × 45 + 40 + envío 10
    assert ana["estado"] == "por_validar"
    assert ana["num_items"] == 3
    assert ana["tiene_comprobante"] is True
    assert bandeja[0]["tiene_comprobante"] is False


def test_filtrar_por_estado(client, auth, pedidos):
    filtrados = client.get("/admin/pedidos", params={"estado": "por_validar"}, headers=auth).json()
    assert [p["numero"] for p in filtrados] == ["AK-0001"]
    assert client.get("/admin/pedidos", params={"estado": "entregado"}, headers=auth).json() == []
    assert client.get("/admin/pedidos", params={"estado": "inventado"}, headers=auth).status_code == 422


def test_buscar_por_numero_nombre_o_telefono(client, auth, pedidos):
    for q in ("AK-0002", "bea", "9222"):
        assert [p["numero"] for p in client.get("/admin/pedidos", params={"q": q}, headers=auth).json()] == ["AK-0002"]


def test_bandeja_vacia(client, auth):
    assert client.get("/admin/pedidos", headers=auth).json() == []


def test_detalle_del_pedido(client, auth, pedidos):
    detalle = client.get("/admin/pedidos/1", headers=auth).json()
    assert detalle["numero"] == "AK-0001"
    assert detalle["clienta"] == {"nombre": "Ana Prueba", "telefono": "911111111", "correo": "clienta@ejemplo.com",
                                  "direccion": "Av. Siempre Viva 123", "referencia": "Frente al parque"}
    assert detalle["distrito"] == "Miraflores"
    assert [(i["variante"], i["cantidad"], i["precio_unitario"], i["subtotal"]) for i in detalle["items"]] == [
        ("Amatista", 2, "45.00", "90.00"), ("Turmalina negra", 1, "40.00", "40.00")]
    assert (detalle["subtotal"], detalle["costo_envio"], detalle["total"]) == ("130.00", "10.00", "140.00")
    assert detalle["comprobante_url"] == "comprobantes/AK-0001.jpg"
    assert [h["estado"] for h in detalle["historial"]] == ["pendiente_pago", "por_validar"]


def test_el_detalle_conserva_el_precio_historico(client, auth, pedidos):
    """Si la propietaria cambia el precio después, el pedido muestra el que pagó la clienta."""
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "60.00", "existencias": 3}, headers=auth)
    amatista = client.get("/admin/pedidos/1", headers=auth).json()["items"][0]
    assert amatista["precio_unitario"] == "45.00"


def test_historial_muestra_quien_hizo_el_cambio(client, auth, pedidos, engine):
    with Session(engine) as db:
        db.add(HistorialEstadoPedido(pedido_id=1, usuario_id=1, estado=EstadoPedido.CONFIRMADO,
                                     fecha=datetime.now(timezone.utc)))
        db.commit()
    historial = client.get("/admin/pedidos/1", headers=auth).json()["historial"]
    assert [(h["estado"], h["usuario"]) for h in historial] == [
        ("pendiente_pago", None), ("por_validar", None), ("confirmado", "duena@example.com")]


def test_pedido_sin_distrito_ni_comprobante(client, auth, pedidos):
    detalle = client.get("/admin/pedidos/2", headers=auth).json()
    assert (detalle["distrito"], detalle["comprobante_url"]) == (None, None)


def test_pedido_inexistente(client, auth):
    assert client.get("/admin/pedidos/99", headers=auth).status_code == 404
