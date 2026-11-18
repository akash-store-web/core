"""HU019: ver las ventas del mes (AKASH-205).

Fechas fijas en el pasado (sep-nov 2026) para los meses cerrados; el mes actual se calcula en hora de Lima.
Los datos de clientas son ficticios."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.pedido import EstadoPedido
from app.services.ventas import mes_anterior, mes_lima, mes_siguiente, nombre_mes
from tests.fabricas import crear_pedido, dar_stock

URL = "/admin/ventas/mes"
ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
}


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


@pytest.fixture
def productos(client, auth):
    """Variante 1 Amatista (S/ 45, 10 u.) y 2 Turmalina (S/ 40, 10 u.)."""
    client.post("/admin/productos", json=ANILLO, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "precio": "45.00"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Turmalina negra"}, headers=auth)
    dar_stock(client, auth, 1, 10)
    dar_stock(client, auth, 2, 10)


@pytest.fixture
def historico(engine, productos):
    """Septiembre: P-0001 confirmado (100 + 10).
    Octubre: P-0002 confirmado (90 + 10), P-0003 entregado (40 + 15), P-0004 pendiente, P-0005 cancelado,
    P-0006 enviado confirmado el 31-oct 22:00 hora de Lima (= 1-nov 03:00 UTC).
    P-0007: creado en octubre pero confirmado en noviembre (cuenta en noviembre)."""
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(1, 2, "50.00")], estado=EstadoPedido.CONFIRMADO, fecha=utc(2026, 9, 25, 15))
        crear_pedido(db, "P-0002", [(1, 2, "45.00")], estado=EstadoPedido.CONFIRMADO, fecha=utc(2026, 10, 5, 15))
        crear_pedido(db, "P-0003", [(2, 1, "40.00")], estado=EstadoPedido.ENTREGADO, fecha=utc(2026, 10, 10, 15),
                     costo_envio="15.00")
        crear_pedido(db, "P-0004", [(2, 3, "40.00")], fecha=utc(2026, 10, 12, 15))
        crear_pedido(db, "P-0005", [(2, 3, "40.00")], estado=EstadoPedido.CANCELADO, fecha=utc(2026, 10, 13, 15))
        crear_pedido(db, "P-0006", [(1, 1, "45.00")], estado=EstadoPedido.ENVIADO, fecha=utc(2026, 10, 31, 20),
                     confirmado_en=utc(2026, 11, 1, 3))
        crear_pedido(db, "P-0007", [(2, 2, "40.00")], estado=EstadoPedido.CONFIRMADO, fecha=utc(2026, 10, 30, 15),
                     confirmado_en=utc(2026, 11, 2, 15), costo_envio="0.00")


def _ventas(client, auth, anio=None, mes=None):
    params = {k: v for k, v in {"anio": anio, "mes": mes}.items() if v is not None}
    return client.get(URL, params=params, headers=auth)


def test_exige_token(client):
    assert client.get(URL).status_code == 401


# --- Escenario 1 y E4: solo confirmados, enviados y entregados ---

def test_ventas_de_un_mes_cerrado(client, auth, historico):
    respuesta = _ventas(client, auth, 2026, 10)
    assert respuesta.status_code == 200, respuesta.text
    ventas = respuesta.json()
    # P-0002 (90 + 10), P-0003 (40 + 15) y P-0006 (45 + 10, confirmado el 31-oct en Lima)
    assert (ventas["anio"], ventas["mes"], ventas["pedidos"]) == (2026, 10, 3)
    assert (ventas["total_productos"], ventas["total_envio"], ventas["total"]) == ("175.00", "35.00", "210.00")
    assert ventas["sin_ventas"] is False
    assert ventas["mensaje"] is None
    assert ventas["mes_anterior"] == {"anio": 2026, "mes": 9, "pedidos": 1, "total_productos": "100.00",
                                      "total_envio": "10.00", "total": "110.00"}


def test_cuenta_en_el_mes_en_que_se_confirmo(client, auth, historico):
    """P-0007 se creó en octubre pero se confirmó en noviembre."""
    ventas = _ventas(client, auth, 2026, 11).json()
    assert ventas["pedidos"] == 1
    assert (ventas["total_productos"], ventas["total_envio"], ventas["total"]) == ("80.00", "0.00", "80.00")
    assert ventas["mes_anterior"]["pedidos"] == 3


def test_limite_del_mes_en_hora_de_lima(client, auth, engine, productos):
    """1-nov 03:00 UTC es todavía 31-oct en Lima; 1-nov 05:00 UTC ya es noviembre."""
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(1, 1, "45.00")], estado=EstadoPedido.CONFIRMADO, fecha=utc(2026, 10, 20),
                     confirmado_en=utc(2026, 11, 1, 4, 59))
        crear_pedido(db, "P-0002", [(1, 1, "45.00")], estado=EstadoPedido.CONFIRMADO, fecha=utc(2026, 10, 20),
                     confirmado_en=utc(2026, 11, 1, 5, 0))
    assert _ventas(client, auth, 2026, 10).json()["pedidos"] == 1
    assert _ventas(client, auth, 2026, 11).json()["pedidos"] == 1


# --- Escenario 2: por defecto, el mes actual ---

def test_por_defecto_el_mes_actual(client, auth, engine, historico):
    with Session(engine) as db:
        crear_pedido(db, "P-0100", [(1, 3, "45.00")], estado=EstadoPedido.CONFIRMADO, costo_envio="10.00")
    anio, mes = mes_lima(datetime.now(timezone.utc))
    ventas = _ventas(client, auth).json()
    assert (ventas["anio"], ventas["mes"]) == (anio, mes)
    assert ventas == _ventas(client, auth, anio, mes).json()
    assert ventas["pedidos"] >= 1
    assert Decimal(ventas["total"]) >= Decimal("145.00")
    assert (ventas["mes_anterior"]["anio"], ventas["mes_anterior"]["mes"]) == mes_anterior(anio, mes)


# --- Escenario 3: sin ventas ---

def test_sin_pedidos_responde_cero_con_mensaje(client, auth):
    anio, mes = mes_lima(datetime.now(timezone.utc))
    ventas = _ventas(client, auth).json()
    assert ventas["pedidos"] == 0
    assert (ventas["total_productos"], ventas["total_envio"], ventas["total"]) == ("0.00", "0.00", "0.00")
    assert ventas["sin_ventas"] is True
    assert ventas["mensaje"] == f"No hubo ventas confirmadas en {nombre_mes(anio, mes)}"
    assert ventas["mes_anterior"]["pedidos"] == 0


def test_mes_sin_ventas_con_pedidos_pendientes(client, auth, engine, productos):
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(1, 1, "45.00")], fecha=utc(2026, 10, 1, 15))
    ventas = _ventas(client, auth, 2026, 10).json()
    assert ventas["sin_ventas"] is True
    assert ventas["mensaje"] == "No hubo ventas confirmadas en octubre de 2026"


# --- E5: mes no válido ---

@pytest.mark.parametrize("params", [{"anio": 2026, "mes": 13}, {"anio": 2026, "mes": 0}, {"anio": 2026},
                                    {"mes": 10}, {"anio": 2026, "mes": "octubre"}])
def test_parametros_no_validos(client, auth, historico, params):
    assert client.get(URL, params=params, headers=auth).status_code == 422


def test_mes_futuro(client, auth, historico):
    anio, mes = mes_siguiente(*mes_lima(datetime.now(timezone.utc)))
    respuesta = _ventas(client, auth, anio, mes)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "No se puede consultar un mes futuro"


def test_mes_anterior_al_primer_pedido(client, auth, historico):
    respuesta = _ventas(client, auth, 2026, 8)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "No hay registros antes de septiembre de 2026"


def test_sin_pedidos_solo_el_mes_actual_es_valido(client, auth):
    anio, mes = mes_anterior(*mes_lima(datetime.now(timezone.utc)))
    assert _ventas(client, auth, anio, mes).status_code == 422


# --- E6: integridad del total ---

def test_total_igual_a_la_suma_de_los_pedidos_confirmados(client, auth, engine, productos):
    with Session(engine) as db:
        for i, (variante, cantidad, envio) in enumerate([(1, 2, "10.00"), (2, 1, "15.00"), (1, 1, "0.00")], 1):
            crear_pedido(db, f"P-000{i}", [(variante, cantidad, "45.00" if variante == 1 else "40.00")],
                         telefono=f"90000000{i}", costo_envio=envio)
        crear_pedido(db, "P-0004", [(2, 1, "40.00")], telefono="900000004")  # queda pendiente
    for pedido_id in (1, 2, 3):
        assert client.patch(f"/admin/pedidos/{pedido_id}/estado", json={"estado": "confirmado"},
                            headers=auth).status_code == 200
    ventas = _ventas(client, auth).json()
    confirmados = [client.get(f"/admin/pedidos/{p['id']}", headers=auth).json()
                   for p in client.get("/admin/pedidos", params={"estado": "confirmado"}, headers=auth).json()]
    assert ventas["pedidos"] == len(confirmados) == 3
    assert Decimal(ventas["total"]) == sum(Decimal(p["total"]) for p in confirmados) == Decimal("200.00")
    assert Decimal(ventas["total_envio"]) == sum(Decimal(p["costo_envio"]) for p in confirmados)
    assert Decimal(ventas["total_productos"]) == sum(Decimal(i["subtotal"]) for p in confirmados for i in p["items"])
    assert Decimal(ventas["total_productos"]) + Decimal(ventas["total_envio"]) == Decimal(ventas["total"])


# --- E7: un confirmado que luego se cancela ya no suma ---

def test_confirmado_luego_cancelado_no_suma(client, auth, engine, productos):
    with Session(engine) as db:
        crear_pedido(db, "P-0001", [(1, 2, "45.00")])
    client.patch("/admin/pedidos/1/estado", json={"estado": "confirmado"}, headers=auth)
    assert _ventas(client, auth).json()["pedidos"] == 1
    client.patch("/admin/pedidos/1/estado", json={"estado": "cancelado"}, headers=auth)
    ventas = _ventas(client, auth).json()
    assert ventas["pedidos"] == 0
    assert ventas["total"] == "0.00"
    assert ventas["sin_ventas"] is True
