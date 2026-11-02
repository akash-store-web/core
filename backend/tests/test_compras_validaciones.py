"""HU033: escenarios de error y alternativos de la compra (E6 / AKASH-152, E9, E10, E13, E16)."""
import pytest
from sqlalchemy.orm import Session

from tests.fabricas import crear_pedido

ROLL_ON = {
    "categoria_id": 5,
    "nombre": "Roll-on de cuarzo",
    "descripcion": "Roll-on de aceite esencial con chips de cuarzo natural.",
    "precio_base": "30.00",
}
BOLETA = {
    "proveedor": "Feria de Caquetá",
    "tipo_comprobante": "boleta",
    "numero_comprobante": "B001-1",
    "fecha": "2026-10-14",
    "items": [{"variante_id": 1, "cantidad": 5, "costo_unitario": "12.00"}],
}


@pytest.fixture
def roll_on(client, auth):
    """Roll-on (precio base 30.00): Amatista (id 1) y Citrino (id 2, precio propio 20.00)."""
    client.post("/admin/productos", json=ROLL_ON, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Citrino", "precio": "20.00"}, headers=auth)


def _comprar(client, auth, **cambios):
    return client.post("/admin/compras", json={**BOLETA, **cambios}, headers=auth)


def _stock(client, auth):
    return {v["nombre"]: v["existencias"] for v in client.get("/admin/productos/1/variantes", headers=auth).json()}


# --- Escenario 6 / AKASH-152: compra sin comprobante con número interno ---

def test_sin_comprobante_recibe_numero_interno_correlativo(client, auth, roll_on):
    primera = _comprar(client, auth, tipo_comprobante="sin_comprobante", numero_comprobante=None)
    assert primera.status_code == 201
    assert (primera.json()["tipo_comprobante"], primera.json()["numero_comprobante"]) == ("sin_comprobante", "SC-0001")
    # Si llega un número, se ignora; el correlativo es global (no por proveedor).
    segunda = _comprar(client, auth, tipo_comprobante="sin_comprobante", numero_comprobante="LO-QUE-SEA",
                       proveedor="Otro proveedor")
    assert segunda.json()["numero_comprobante"] == "SC-0002"
    sin_campo = {k: v for k, v in BOLETA.items() if k != "numero_comprobante"}
    tercera = client.post("/admin/compras", json={**sin_campo, "tipo_comprobante": "sin_comprobante"}, headers=auth)
    assert tercera.json()["numero_comprobante"] == "SC-0003"
    assert _stock(client, auth)["Amatista"] == 15


def test_las_boletas_no_alteran_el_correlativo_interno(client, auth, roll_on):
    _comprar(client, auth, numero_comprobante="SC-0050")  # una boleta cuyo número se parece al interno
    assert _comprar(client, auth, tipo_comprobante="sin_comprobante").json()["numero_comprobante"] == "SC-0001"


def test_boleta_y_factura_exigen_numero(client, auth, roll_on):
    sin_numero = {k: v for k, v in BOLETA.items() if k != "numero_comprobante"}
    respuesta = client.post("/admin/compras", json=sin_numero, headers=auth)
    assert respuesta.status_code == 422
    assert "número de comprobante es obligatorio" in respuesta.text


# --- E13: factura sin RUC ---

def test_factura_exige_ruc(client, auth, roll_on):
    respuesta = _comprar(client, auth, tipo_comprobante="factura", numero_comprobante="F001-9")
    assert respuesta.status_code == 422
    assert "RUC" in respuesta.text
    assert _comprar(client, auth, tipo_comprobante="factura", numero_comprobante="F001-9",
                    proveedor_ruc="20512345678").status_code == 201


# --- Rangos de cantidad y costo ---

@pytest.mark.parametrize("item", [
    {"variante_id": 1, "cantidad": 10001, "costo_unitario": "1.00"},
    {"variante_id": 1, "cantidad": 2.5, "costo_unitario": "1.00"},
    {"variante_id": 1, "cantidad": 1, "costo_unitario": "10000.00"},
    {"variante_id": 1, "cantidad": 1, "costo_unitario": "1.234"},
])
def test_cantidad_y_costo_fuera_de_rango(client, auth, roll_on, item):
    assert _comprar(client, auth, items=[item]).status_code == 422
    assert _stock(client, auth) == {"Amatista": 0, "Citrino": 0}


def test_limites_exactos(client, auth, roll_on):
    item = {"variante_id": 1, "cantidad": 10000, "costo_unitario": "9999.99"}
    assert _comprar(client, auth, items=[item], confirmar_avisos=True).status_code == 201


# --- E9 y E10: avisos que piden confirmación ---

def test_costo_cero_o_mayor_al_precio_pide_confirmacion(client, auth, roll_on):
    items = [{"variante_id": 1, "cantidad": 2, "costo_unitario": "0.00"},
             {"variante_id": 2, "cantidad": 3, "costo_unitario": "25.00"}]  # Citrino se vende a 20.00
    respuesta = _comprar(client, auth, items=items)
    assert respuesta.status_code == 409
    detalle = respuesta.json()["detail"]
    assert "confirmar_avisos" in detalle["mensaje"]
    assert len(detalle["avisos"]) == 2
    assert detalle["avisos"][0].startswith("Línea 1 (Roll-on de cuarzo · Amatista): el costo unitario es 0.00")
    assert "25.00 es mayor al precio de venta 20.00" in detalle["avisos"][1]
    assert _stock(client, auth) == {"Amatista": 0, "Citrino": 0}
    assert client.get("/admin/compras", headers=auth).json() == []

    confirmada = _comprar(client, auth, items=items, confirmar_avisos=True)
    assert confirmada.status_code == 201
    assert _stock(client, auth) == {"Amatista": 2, "Citrino": 3}


def test_costo_igual_al_precio_no_avisa(client, auth, roll_on):
    item = {"variante_id": 2, "cantidad": 1, "costo_unitario": "20.00"}
    assert _comprar(client, auth, items=[item]).status_code == 201


# --- E16: variante desactivada ---

def test_no_se_compra_una_variante_desactivada(client, auth, roll_on, engine):
    with Session(engine) as db:
        crear_pedido(db, "AK-0001", [(2, 1, "20.00")])
    assert client.delete("/admin/productos/1/variantes/2", headers=auth).json()["desactivada"] is True
    respuesta = _comprar(client, auth, items=[{"variante_id": 2, "cantidad": 1, "costo_unitario": "5.00"}])
    assert respuesta.status_code == 422
    assert "desactivadas" in respuesta.json()["detail"] and "Citrino" in respuesta.json()["detail"]
    assert client.get("/admin/compras", headers=auth).json() == []
