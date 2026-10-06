"""HU026: configurar zonas de cobertura y costos de envío."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.envios import calcular_costo_envio

LIMA = {"nombre": "Lima — motorizado", "costo": "10.00"}
CALLAO = {"nombre": "Callao — motorizado", "costo": "15.00"}


def _zona(client, auth, **datos):
    respuesta = client.post("/admin/zonas-envio", json=datos or LIMA, headers=auth)
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def _distrito(client, auth, nombre, zona_envio_id=None):
    respuesta = client.post("/admin/distritos", json={"nombre": nombre, "zona_envio_id": zona_envio_id}, headers=auth)
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


# --- Panel ---

def test_rutas_del_panel_exigen_token(client):
    assert client.get("/admin/zonas-envio").status_code == 401
    assert client.post("/admin/zonas-envio", json=LIMA).status_code == 401
    assert client.put("/admin/zonas-envio/1", json=LIMA).status_code == 401
    assert client.put("/admin/zonas-envio/1/distritos", json={"distrito_ids": [1]}).status_code == 401
    assert client.get("/admin/distritos").status_code == 401
    assert client.post("/admin/distritos", json={"nombre": "Miraflores"}).status_code == 401
    assert client.put("/admin/distritos/1", json={"nombre": "Miraflores"}).status_code == 401


def test_crear_y_listar_zonas(client, auth):
    _zona(client, auth)
    _zona(client, auth, **CALLAO)
    zonas = client.get("/admin/zonas-envio", headers=auth).json()
    assert [(z["nombre"], z["costo"], z["activa"]) for z in zonas] == [
        ("Callao — motorizado", "15.00", True),
        ("Lima — motorizado", "10.00", True),
    ]


def test_validaciones_de_zona(client, auth):
    assert client.post("/admin/zonas-envio", json={"nombre": "Lima"}, headers=auth).status_code == 422
    assert client.post("/admin/zonas-envio", json={"nombre": " ", "costo": "5"}, headers=auth).status_code == 422
    assert client.post("/admin/zonas-envio", json={"nombre": "Lima", "costo": "-1"}, headers=auth).status_code == 422
    assert client.post("/admin/zonas-envio", json={"nombre": "Lima", "costo": "5.555"}, headers=auth).status_code == 422
    assert client.post("/admin/zonas-envio", json={"nombre": "Recojo", "costo": "0"}, headers=auth).status_code == 201
    assert client.put("/admin/zonas-envio/99", json=LIMA, headers=auth).status_code == 404


def test_cambio_de_costo_se_aplica_de_inmediato(client, auth):
    """HU026 criterio 1: al guardar, el checkout aplica el costo nuevo."""
    zona = _zona(client, auth)
    distrito = _distrito(client, auth, "Miraflores", zona)
    assert client.get("/envio/costo", params={"distrito_id": distrito}).json()["costo_envio"] == "10.00"
    client.put(f"/admin/zonas-envio/{zona}", json={**LIMA, "costo": "12.00"}, headers=auth)
    assert client.get("/envio/costo", params={"distrito_id": distrito}).json()["costo_envio"] == "12.00"


def test_crear_distritos_y_validaciones(client, auth):
    zona = _zona(client, auth)
    _distrito(client, auth, "Miraflores", zona)
    assert client.post("/admin/distritos", json={"nombre": "miraflores"}, headers=auth).status_code == 409
    assert client.post("/admin/distritos", json={"nombre": ""}, headers=auth).status_code == 422
    assert client.post("/admin/distritos", json={"nombre": "Surco", "zona_envio_id": 99}, headers=auth).status_code == 422


def test_asignar_distritos_a_una_zona(client, auth):
    zona = _zona(client, auth)
    ids = [_distrito(client, auth, n) for n in ("Miraflores", "Surquillo", "Barranco")]
    respuesta = client.put(f"/admin/zonas-envio/{zona}/distritos", json={"distrito_ids": ids[:2]}, headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["num_distritos"] == 2
    sin_zona = client.get("/admin/distritos", params={"sin_zona": True}, headers=auth).json()
    assert [d["nombre"] for d in sin_zona] == ["Barranco"]
    de_lima = client.get("/admin/distritos", params={"zona_envio_id": zona}, headers=auth).json()
    assert [d["nombre"] for d in de_lima] == ["Miraflores", "Surquillo"]


def test_asignar_distrito_inexistente(client, auth):
    zona = _zona(client, auth)
    respuesta = client.put(f"/admin/zonas-envio/{zona}/distritos", json={"distrito_ids": [99]}, headers=auth)
    assert respuesta.status_code == 404
    assert client.put(f"/admin/zonas-envio/{zona}/distritos", json={"distrito_ids": []}, headers=auth).status_code == 422


def test_mover_distrito_y_quitar_cobertura(client, auth):
    lima = _zona(client, auth)
    callao = _zona(client, auth, **CALLAO)
    distrito = _distrito(client, auth, "Bellavista", lima)
    respuesta = client.put(f"/admin/distritos/{distrito}", json={"nombre": "Bellavista", "zona_envio_id": callao}, headers=auth)
    assert respuesta.json()["zona_envio_id"] == callao
    respuesta = client.put(f"/admin/distritos/{distrito}", json={"nombre": "Bellavista", "zona_envio_id": None}, headers=auth)
    assert respuesta.json()["con_cobertura"] is False
    assert client.put("/admin/distritos/99", json={"nombre": "X"}, headers=auth).status_code == 404


# --- Público (checkout) ---

def test_endpoints_publicos_no_exigen_login(client, auth):
    zona = _zona(client, auth)
    _distrito(client, auth, "Miraflores", zona)
    assert client.get("/envio/distritos").status_code == 200
    assert client.get("/envio/costo", params={"distrito_id": 1}).status_code == 200


def test_listado_publico_con_costos(client, auth):
    zona = _zona(client, auth)
    _distrito(client, auth, "Miraflores", zona)
    _distrito(client, auth, "Ancón")
    distritos = client.get("/envio/distritos").json()
    assert distritos == [
        {"id": 2, "nombre": "Ancón", "con_cobertura": False, "costo_envio": None},
        {"id": 1, "nombre": "Miraflores", "con_cobertura": True, "costo_envio": "10.00"},
    ]


def test_distrito_sin_cobertura(client, auth, engine):
    """HU026 #5: distrito sin zona, o con la zona desactivada, no tiene cobertura."""
    zona = _zona(client, auth)
    sin_zona = _distrito(client, auth, "Ancón")
    con_zona = _distrito(client, auth, "Miraflores", zona)

    respuesta = client.get("/envio/costo", params={"distrito_id": sin_zona}).json()
    assert (respuesta["con_cobertura"], respuesta["costo_envio"]) == (False, None)

    client.put(f"/admin/zonas-envio/{zona}", json={**LIMA, "activa": False}, headers=auth)
    respuesta = client.get("/envio/costo", params={"distrito_id": con_zona}).json()
    assert (respuesta["con_cobertura"], respuesta["costo_envio"]) == (False, None)

    # El pedido (HU010) usará calcular_costo_envio, que rechaza distritos sin cobertura.
    with Session(engine) as db:
        with pytest.raises(HTTPException) as error:
            calcular_costo_envio(db, sin_zona)
        assert error.value.status_code == 422


def test_calcular_costo_envio_con_cobertura(client, auth, engine):
    zona = _zona(client, auth)
    distrito = _distrito(client, auth, "Miraflores", zona)
    with Session(engine) as db:
        assert str(calcular_costo_envio(db, distrito)) == "10.00"


def test_distrito_inexistente(client):
    assert client.get("/envio/costo", params={"distrito_id": 99}).status_code == 404
    assert client.get("/envio/costo").status_code == 422
