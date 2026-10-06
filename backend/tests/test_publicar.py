"""HU016: publicar y despublicar productos."""
from sqlalchemy.orm import Session

from app import config
from app.models.imagen import Imagen
from app.models.variante import Variante

COLLAR = {
    "categoria_id": 3,
    "nombre": "Collar de amatista",
    "descripcion": "Collar con dije de amatista natural y cadena de acero quirúrgico.",
    "precio_base": "35.00",
}
URL = "/admin/productos/1/publicado"


def _producto(client, auth):
    assert client.post("/admin/productos", json=COLLAR, headers=auth).status_code == 201


def _publicar(client, auth, valor=True):
    return client.patch(URL, json={"publicado": valor}, headers=auth)


def test_exige_token(client):
    assert client.patch(URL, json={"publicado": True}).status_code == 401


def test_publicar_y_despublicar(client, auth):
    _producto(client, auth)
    respuesta = _publicar(client, auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["publicado"] is True
    assert client.get("/admin/productos", headers=auth).json()[0]["publicado"] is True

    respuesta = _publicar(client, auth, False)
    assert respuesta.status_code == 200
    assert respuesta.json()["publicado"] is False


def test_despublicar_no_borra_la_informacion(client, auth):
    _producto(client, auth)
    _publicar(client, auth)
    _publicar(client, auth, False)
    producto = client.get("/admin/productos/1", headers=auth).json()
    assert producto["nombre"] == "Collar de amatista"
    assert producto["precio_base"] == "35.00"
    assert len(client.get("/admin/productos/1/variantes", headers=auth).json()) == 1


def test_publicar_es_idempotente(client, auth):
    _producto(client, auth)
    assert _publicar(client, auth).status_code == 200
    assert _publicar(client, auth).json()["publicado"] is True


def test_no_publica_sin_variantes(client, auth, engine):
    _producto(client, auth)
    with Session(engine) as db:  # caso defensivo: datos cargados por fuera de la API
        db.query(Variante).delete()
        db.commit()
    respuesta = _publicar(client, auth)
    assert respuesta.status_code == 409
    assert "variante" in respuesta.json()["detail"]


def test_sin_regla_de_foto_se_publica_sin_imagenes(client, auth, monkeypatch):
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", False)
    _producto(client, auth)
    assert _publicar(client, auth).status_code == 200


def test_con_regla_de_foto_bloquea_publicacion_incompleta(client, auth, engine, monkeypatch):
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", True)
    _producto(client, auth)
    respuesta = _publicar(client, auth)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "No se puede publicar: falta al menos una foto"

    with Session(engine) as db:
        db.add(Imagen(producto_id=1, url="https://ejemplo/collar.jpg", es_principal=True))
        db.commit()
    assert _publicar(client, auth).status_code == 200


def test_despublicar_siempre_se_permite(client, auth, monkeypatch):
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", True)
    _producto(client, auth)
    assert _publicar(client, auth, False).status_code == 200


def test_validaciones(client, auth):
    _producto(client, auth)
    assert client.patch(URL, json={}, headers=auth).status_code == 422
    assert client.patch(URL, json={"publicado": "tal vez"}, headers=auth).status_code == 422
    assert client.patch("/admin/productos/99/publicado", json={"publicado": True}, headers=auth).status_code == 404


def test_editar_no_cambia_el_estado_de_publicacion(client, auth):
    _producto(client, auth)
    _publicar(client, auth)
    respuesta = client.put("/admin/productos/1", json={**COLLAR, "precio_base": "38.00"}, headers=auth)
    assert respuesta.json()["publicado"] is True
