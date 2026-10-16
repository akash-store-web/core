"""HU033: registrar la compra de mercadería con su comprobante (pruebas AKASH-118)."""
from datetime import date, timedelta

import pytest

ROLL_ON = {
    "categoria_id": 5,
    "nombre": "Roll-on de cuarzo",
    "descripcion": "Roll-on de aceite esencial con chips de cuarzo natural.",
    "precio_base": "30.00",
}
FACTURA = {
    "proveedor": "Minerales del Sur",
    "proveedor_ruc": "20512345678",
    "tipo_comprobante": "factura",
    "numero_comprobante": "F001-000123",
    "fecha": "2026-10-14",
    "items": [
        {"variante_id": 1, "cantidad": 10, "costo_unitario": "12.50"},
        {"variante_id": 2, "cantidad": 4, "costo_unitario": "15.00"},
    ],
}


@pytest.fixture
def roll_on(client, auth):
    """Roll-on sin stock con dos variantes: Amatista (id 1) y Citrino (id 2)."""
    client.post("/admin/productos", json=ROLL_ON, headers=auth)
    client.put("/admin/productos/1/variantes/1", json={"nombre": "Amatista"}, headers=auth)
    client.post("/admin/productos/1/variantes", json={"nombre": "Citrino"}, headers=auth)


def _comprar(client, auth, **cambios):
    return client.post("/admin/compras", json={**FACTURA, **cambios}, headers=auth)


def _stock(client, auth):
    return {v["nombre"]: v["existencias"] for v in client.get("/admin/productos/1/variantes", headers=auth).json()}


def test_exige_token(client):
    assert client.post("/admin/compras", json=FACTURA).status_code == 401
    assert client.get("/admin/compras").status_code == 401
    assert client.get("/admin/compras/1").status_code == 401
    assert client.get("/admin/productos/1/compras").status_code == 401


# --- Escenario 1: registro de la compra ---

def test_registrar_compra(client, auth, roll_on):
    respuesta = _comprar(client, auth)
    assert respuesta.status_code == 201
    compra = respuesta.json()
    assert (compra["proveedor"], compra["proveedor_ruc"], compra["tipo_comprobante"], compra["numero_comprobante"]) == (
        "Minerales del Sur", "20512345678", "factura", "F001-000123")
    assert compra["fecha"] == "2026-10-14"
    assert compra["total"] == "185.00"  # 10 × 12.50 + 4 × 15.00
    assert compra["unidades"] == 14
    assert compra["usuario"] == "duena@example.com"
    assert compra["tiene_comprobante"] is False
    assert [(i["variante"], i["cantidad"], i["costo_unitario"], i["subtotal"]) for i in compra["items"]] == [
        ("Amatista", 10, "12.50", "125.00"), ("Citrino", 4, "15.00", "60.00")]


def test_boleta_sin_ruc(client, auth, roll_on):
    respuesta = _comprar(client, auth, tipo_comprobante="boleta", numero_comprobante="b001-77", proveedor_ruc=None)
    assert respuesta.status_code == 201
    assert respuesta.json()["numero_comprobante"] == "B001-77"  # se normaliza en mayúsculas


@pytest.mark.parametrize("cambio", [
    {"proveedor": ""},
    {"proveedor_ruc": "123"},
    {"tipo_comprobante": "recibo"},
    {"numero_comprobante": "  "},
    {"fecha": (date.today() + timedelta(days=1)).isoformat()},
    {"items": []},
    {"items": [{"variante_id": 1, "cantidad": 0, "costo_unitario": "1.00"}]},
    {"items": [{"variante_id": 1, "cantidad": 2, "costo_unitario": "-1"}]},
    {"items": [{"variante_id": 1, "cantidad": 2}]},  # costo unitario obligatorio
    {"items": [{"variante_id": 1, "cantidad": 2, "costo_unitario": "1.00"},
               {"variante_id": 1, "cantidad": 3, "costo_unitario": "1.00"}]},  # variante repetida
])
def test_validaciones(client, auth, roll_on, cambio):
    assert _comprar(client, auth, **cambio).status_code == 422
    assert _stock(client, auth) == {"Amatista": 0, "Citrino": 0}


def test_variante_inexistente_no_guarda_nada(client, auth, roll_on):
    items = [{"variante_id": 1, "cantidad": 5, "costo_unitario": "10.00"},
             {"variante_id": 99, "cantidad": 1, "costo_unitario": "10.00"}]
    assert _comprar(client, auth, items=items).status_code == 422
    assert client.get("/admin/compras", headers=auth).json() == []
    assert _stock(client, auth) == {"Amatista": 0, "Citrino": 0}


# --- Escenario 3: ingreso de stock (con movimiento «compra», HU034) ---

def test_la_compra_suma_existencias_y_deja_movimientos(client, auth, roll_on):
    compra_id = _comprar(client, auth).json()["id"]
    assert _stock(client, auth) == {"Amatista": 10, "Citrino": 4}
    movimientos = client.get("/admin/productos/1/movimientos", headers=auth).json()
    assert sorted((m["variante"], m["tipo"], m["cantidad"], m["saldo"], m["compra_id"]) for m in movimientos) == [
        ("Amatista", "compra", 10, 10, compra_id), ("Citrino", "compra", 4, 4, compra_id)]


def test_las_compras_se_acumulan(client, auth, roll_on):
    _comprar(client, auth)
    _comprar(client, auth, numero_comprobante="F001-000124", items=[{"variante_id": 1, "cantidad": 3, "costo_unitario": "13.00"}])
    assert _stock(client, auth)["Amatista"] == 13
    assert client.get("/admin/variantes/1/movimientos", headers=auth).json()[0]["saldo"] == 13


def test_la_compra_hace_disponible_el_producto_en_el_catalogo(client, auth, roll_on):
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    assert client.get("/catalogo").json()[0]["disponible"] is False
    _comprar(client, auth)
    assert client.get("/catalogo").json()[0]["disponible"] is True


# --- Escenario 4: trazabilidad por producto ---

def test_compras_con_las_que_ingreso_el_stock_del_producto(client, auth, roll_on):
    _comprar(client, auth, fecha="2026-10-10")
    _comprar(client, auth, numero_comprobante="F001-000200", fecha="2026-10-14",
             items=[{"variante_id": 2, "cantidad": 6, "costo_unitario": "14.00"}])
    ingresos = client.get("/admin/productos/1/compras", headers=auth).json()
    assert [(i["fecha"], i["numero_comprobante"], i["variante"], i["cantidad"], i["costo_unitario"]) for i in ingresos] == [
        ("2026-10-14", "F001-000200", "Citrino", 6, "14.00"),
        ("2026-10-10", "F001-000123", "Amatista", 10, "12.50"),
        ("2026-10-10", "F001-000123", "Citrino", 4, "15.00"),
    ]
    assert client.get("/admin/productos/99/compras", headers=auth).status_code == 404


# --- Escenario 5: comprobante duplicado ---

def test_comprobante_duplicado_no_suma_dos_veces(client, auth, roll_on):
    assert _comprar(client, auth).status_code == 201
    # mismo proveedor (otra capitalización) y mismo número (en minúsculas): es el mismo comprobante
    respuesta = _comprar(client, auth, proveedor="MINERALES DEL SUR", numero_comprobante="f001-000123")
    assert respuesta.status_code == 409
    assert "ya está registrado" in respuesta.json()["detail"]
    assert _stock(client, auth) == {"Amatista": 10, "Citrino": 4}
    assert len(client.get("/admin/compras", headers=auth).json()) == 1


def test_mismo_numero_de_otro_proveedor_o_tipo_si_se_permite(client, auth, roll_on):
    assert _comprar(client, auth).status_code == 201
    assert _comprar(client, auth, proveedor="Cristales Andinos").status_code == 201
    assert _comprar(client, auth, tipo_comprobante="boleta").status_code == 201


# --- Listado y detalle ---

def test_listado_filtrado_y_detalle(client, auth, roll_on):
    _comprar(client, auth, fecha="2026-10-01")
    _comprar(client, auth, proveedor="Cristales Andinos", fecha="2026-10-12")
    todas = client.get("/admin/compras", headers=auth).json()
    assert [c["proveedor"] for c in todas] == ["Cristales Andinos", "Minerales del Sur"]  # más reciente primero
    assert [c["proveedor"] for c in client.get("/admin/compras", params={"proveedor": "andinos"},
                                               headers=auth).json()] == ["Cristales Andinos"]
    assert [c["fecha"] for c in client.get("/admin/compras", params={"desde": "2026-10-05"}, headers=auth).json()] == [
        "2026-10-12"]
    detalle = client.get(f"/admin/compras/{todas[0]['id']}", headers=auth).json()
    assert detalle["proveedor"] == "Cristales Andinos" and len(detalle["items"]) == 2
    assert client.get("/admin/compras/99", headers=auth).status_code == 404
