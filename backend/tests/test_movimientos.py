"""HU034: mover el stock solo con movimientos registrados (pruebas AKASH-122, AKASH-123 y AKASH-125)."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.movimiento_stock import MovimientoStock, TipoMovimiento
from app.models.variante import Variante
from app.services.movimientos import registrar_movimiento
from scripts.inventario_inicial import registrar as registrar_inventario_inicial
from tests.fabricas import crear_pedido, dar_stock

ROLL_ON = {
    "categoria_id": 5,
    "nombre": "Roll-on de cuarzo",
    "descripcion": "Roll-on de aceite esencial con esfera y chips de cuarzo natural.",
    "precio_base": "30.00",
}


@pytest.fixture
def roll_on(client, auth):
    """Roll-on con dos variantes sin stock: Amatista (id 1) y Citrino (id 2)."""
    client.post("/admin/productos", json=ROLL_ON, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Citrino"}, headers=auth)


def _ajuste(client, auth, variante_id=1, **datos):
    return client.post(f"/admin/variantes/{variante_id}/ajustes", json=datos, headers=auth)


def _existencias(client, auth, variante_id):
    return next(v["existencias"] for v in client.get("/admin/productos/1/variantes", headers=auth).json()
                if v["id"] == variante_id)


# --- Escenario 1: sin edición manual ---

def test_ya_no_existe_el_ajuste_manual_de_stock(client, auth, roll_on):
    assert client.patch("/admin/variantes/1/stock", json={"cambio": 1}, headers=auth).status_code in (404, 405)


def test_crear_o_editar_no_cambia_el_stock(client, auth, roll_on):
    client.post("/admin/productos/1/variantes", json={"nombre": "Jade", "existencias": 9}, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista", "existencias": 9}, headers=auth)
    assert [v["existencias"] for v in client.get("/admin/productos/1/variantes", headers=auth).json()] == [0, 0, 0]
    assert client.get("/admin/productos/1/movimientos", headers=auth).json() == []


# --- Escenario 4: ajuste con motivo ---

def test_ajuste_con_motivo_cambia_el_stock_y_queda_registrado(client, auth, roll_on):
    dar_stock(client, auth, 1, 5)
    respuesta = _ajuste(client, auth, cantidad=-1, motivo="Se rompió al empacar")
    assert respuesta.status_code == 201
    movimiento = respuesta.json()
    assert (movimiento["tipo"], movimiento["cantidad"], movimiento["saldo"]) == ("ajuste", -1, 4)
    assert movimiento["motivo"] == "Se rompió al empacar"
    assert movimiento["variante"] == "Amatista"
    assert movimiento["usuario"] == "duena@example.com"
    assert _existencias(client, auth, 1) == 4


def test_ajuste_sin_motivo_es_rechazado(client, auth, roll_on):
    for datos in ({"cantidad": 2}, {"cantidad": 2, "motivo": ""}, {"cantidad": 2, "motivo": "   "},
                  {"cantidad": 2, "motivo": "ab"}):
        assert _ajuste(client, auth, **datos).status_code == 422, datos
    assert _existencias(client, auth, 1) == 0


def test_ajuste_con_cantidad_cero_o_sin_cantidad(client, auth, roll_on):
    assert _ajuste(client, auth, cantidad=0, motivo="Conteo").status_code == 422
    assert _ajuste(client, auth, motivo="Conteo").status_code == 422


def test_el_stock_nunca_queda_negativo(client, auth, roll_on):
    dar_stock(client, auth, 1, 2)
    respuesta = _ajuste(client, auth, cantidad=-3, motivo="Perdido en el traslado")
    assert respuesta.status_code == 409
    assert _existencias(client, auth, 1) == 2
    assert len(client.get("/admin/variantes/1/movimientos", headers=auth).json()) == 1  # el rechazado no se guarda


def test_ajuste_de_variante_inexistente_y_sin_token(client, auth, roll_on):
    assert _ajuste(client, auth, variante_id=99, cantidad=1, motivo="Conteo").status_code == 404
    assert client.post("/admin/variantes/1/ajustes", json={"cantidad": 1, "motivo": "Conteo"}).status_code == 401


# --- Escenario 5: historial con saldo ---

def test_historial_de_la_variante_con_saldo_tras_cada_movimiento(client, auth, roll_on):
    dar_stock(client, auth, 1, 5, "Mal contado en el inventario")
    _ajuste(client, auth, cantidad=-2, motivo="Se rompieron dos")
    _ajuste(client, auth, cantidad=1, motivo="Apareció en el almacén")
    historial = client.get("/admin/variantes/1/movimientos", headers=auth).json()
    assert [(m["cantidad"], m["saldo"]) for m in historial] == [(1, 4), (-2, 3), (5, 5)]  # más reciente primero
    assert all(m["tipo"] == "ajuste" and m["fecha"] for m in historial)
    assert historial[0]["saldo"] == _existencias(client, auth, 1)  # el último saldo = existencias actuales


def test_historial_del_producto_incluye_todas_sus_variantes(client, auth, roll_on):
    dar_stock(client, auth, 1, 3)
    dar_stock(client, auth, 2, 4)
    historial = client.get("/admin/productos/1/movimientos", headers=auth).json()
    assert sorted((m["variante"], m["saldo"]) for m in historial) == [("Amatista", 3), ("Citrino", 4)]


def test_historial_inexistente_y_sin_token(client, auth, roll_on):
    assert client.get("/admin/variantes/99/movimientos", headers=auth).status_code == 404
    assert client.get("/admin/productos/99/movimientos", headers=auth).status_code == 404
    assert client.get("/admin/variantes/1/movimientos").status_code == 401


# --- Servicio (lo usarán compras HU033 y ventas HU010/HU018) ---

def test_venta_resta_stock_y_guarda_el_pedido(client, auth, roll_on, engine):
    dar_stock(client, auth, 1, 3)
    with Session(engine) as db:
        pedido = crear_pedido(db, "AK-0001", [(1, 2, "30.00")])
        registrar_movimiento(db, 1, -2, TipoMovimiento.VENTA, pedido_id=pedido.id)
        db.commit()
    venta = client.get("/admin/variantes/1/movimientos", headers=auth).json()[0]
    assert (venta["tipo"], venta["cantidad"], venta["saldo"], venta["pedido_numero"]) == ("venta", -2, 1, "AK-0001")
    assert venta["usuario"] is None  # registrado por el sistema


def test_el_servicio_valida_tipo_cantidad_y_motivo(engine, client, auth, roll_on):
    with Session(engine) as db:
        with pytest.raises(ValueError):
            registrar_movimiento(db, 1, 1, "regalo")
        with pytest.raises(ValueError):
            registrar_movimiento(db, 1, 0, TipoMovimiento.COMPRA)
        with pytest.raises(HTTPException) as error:
            registrar_movimiento(db, 1, 1, TipoMovimiento.AJUSTE)
        assert error.value.status_code == 422


# --- Inventario inicial (stock que existía antes de HU034) ---

def test_inventario_inicial_respalda_el_stock_existente_una_sola_vez(client, auth, roll_on, engine):
    with Session(engine) as db:  # stock cargado "a mano" antes de HU034, sin movimientos
        db.get(Variante, 1).existencias = 7
        db.commit()
        assert registrar_inventario_inicial(db, aplicar=False) == 1
        assert db.query(MovimientoStock).count() == 0  # la simulación no escribe
        assert registrar_inventario_inicial(db, aplicar=True) == 1
        assert registrar_inventario_inicial(db, aplicar=True) == 0  # idempotente
    historial = client.get("/admin/variantes/1/movimientos", headers=auth).json()
    assert [(m["tipo"], m["cantidad"], m["saldo"]) for m in historial] == [("inventario_inicial", 7, 7)]
    assert _existencias(client, auth, 1) == 7  # el saldo no cambia: solo queda respaldado
