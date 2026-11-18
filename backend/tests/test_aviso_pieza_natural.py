"""HU006 (AKASH-172): aviso de variación natural en la ficha y en el carrito. Datos ficticios."""
import pytest

from app import config
from tests.fabricas import dar_stock

DEFECTO = config.AVISO_PIEZA_NATURAL_DEFECTO


def _producto(client, auth, nombre, natural, precio="40.00"):
    pid = client.post("/admin/productos", json={
        "categoria_id": 4, "nombre": nombre, "descripcion": f"{nombre} de prueba.", "precio_base": precio,
        "es_pieza_natural": natural}, headers=auth).json()["id"]
    vid = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
    dar_stock(client, auth, vid, 3)
    client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth)
    return pid, vid


@pytest.fixture
def tienda(client, auth):
    """Dos piezas naturales (una con dos piedras) y un producto que no lo es."""
    anillo, amatista = _producto(client, auth, "Anillo con piedra", True)
    turmalina = client.post(f"/admin/productos/{anillo}/variantes", json={"nombre": "Turmalina"},
                            headers=auth).json()["id"]
    dar_stock(client, auth, turmalina, 2)
    pulsera, cuarzo = _producto(client, auth, "Pulsera de cuarzo", True)
    vela, vela_v = _producto(client, auth, "Vela de soya", False)
    return {"anillo": anillo, "amatista": amatista, "turmalina": turmalina, "pulsera": pulsera,
            "cuarzo": cuarzo, "vela": vela, "vela_v": vela_v}


def _carrito(client, *variantes):
    respuesta = client.post("/carrito/validar", json={"items": [{"variante_id": v, "cantidad": 1} for v in variantes]})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_ficha_de_pieza_natural_trae_el_aviso(client, tienda):
    """HU006 Esc.1."""
    ficha = client.get(f"/catalogo/{tienda['anillo']}").json()
    assert ficha["es_pieza_natural"] is True
    assert ficha["aviso_pieza_natural"] == DEFECTO


def test_ficha_sin_pieza_natural_no_trae_aviso(client, tienda):
    """HU006 Esc.3 / E5."""
    assert client.get(f"/catalogo/{tienda['vela']}").json()["aviso_pieza_natural"] is None


def test_texto_configurable(client, tienda, monkeypatch):
    monkeypatch.setattr(config, "AVISO_PIEZA_NATURAL", "  Piedra natural: cada una es distinta.  ")
    assert client.get(f"/catalogo/{tienda['anillo']}").json()["aviso_pieza_natural"] == "Piedra natural: cada una es distinta."


@pytest.mark.parametrize("valor", ["", "   ", "x" * 301])
def test_texto_vacio_o_largo_usa_el_de_defecto(client, tienda, monkeypatch, valor):
    """HU006 E4."""
    monkeypatch.setattr(config, "AVISO_PIEZA_NATURAL", valor)
    assert client.get(f"/catalogo/{tienda['anillo']}").json()["aviso_pieza_natural"] == DEFECTO


def test_texto_de_300_caracteres_se_acepta(client, tienda, monkeypatch):
    monkeypatch.setattr(config, "AVISO_PIEZA_NATURAL", "x" * 300)
    assert client.get(f"/catalogo/{tienda['anillo']}").json()["aviso_pieza_natural"] == "x" * 300


def test_carrito_con_varias_piezas_naturales_muestra_un_solo_aviso(client, tienda):
    """HU006 Esc.2 / E6: una sola vez, con los productos sin repetir (dos piedras del mismo anillo)."""
    cuerpo = _carrito(client, tienda["amatista"], tienda["turmalina"], tienda["cuarzo"], tienda["vela_v"])
    assert cuerpo["aviso_pieza_natural"] == {"texto": DEFECTO, "productos": ["Anillo con piedra", "Pulsera de cuarzo"]}
    assert [i["es_pieza_natural"] for i in cuerpo["items"]] == [True, True, True, False]  # se mantiene por ítem


def test_carrito_sin_piezas_naturales_no_trae_aviso(client, tienda):
    assert _carrito(client, tienda["vela_v"])["aviso_pieza_natural"] is None


def test_producto_no_disponible_no_cuenta_para_el_aviso(client, auth, tienda):
    client.patch(f"/admin/productos/{tienda['pulsera']}/publicado", json={"publicado": False}, headers=auth)
    cuerpo = _carrito(client, tienda["cuarzo"], tienda["vela_v"])
    assert cuerpo["aviso_pieza_natural"] is None
