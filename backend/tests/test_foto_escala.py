"""HU004 (AKASH-164): foto de referencia de escala (máximo una por producto). Storage simulado."""
from tests.test_imagenes import COLLAR, JPG, bucket  # noqa: F401  (fixture de pytest)

URL = "/admin/productos/1/imagenes"


def _preparar(client, auth, fotos=3):
    assert client.post("/admin/productos", json=COLLAR, headers=auth).status_code == 201
    ids = [client.post(URL, files={"foto": (f"f{i}.jpg", JPG, "image/jpeg")}, headers=auth).json()["id"]
           for i in range(fotos)]
    return ids


def _escala(client, auth, imagen_id, valor=True, producto_id=1):
    return client.patch(f"/admin/productos/{producto_id}/imagenes/{imagen_id}/escala",
                        json={"es_referencia_escala": valor}, headers=auth)


def _marcadas(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return [i["id"] for i in respuesta.json() if i["es_referencia_escala"]]


def test_exige_token(client):
    assert client.patch(f"{URL}/1/escala", json={"es_referencia_escala": True}).status_code == 401


def test_marcar_foto_de_escala(client, auth, bucket):
    """HU004 Esc.1: la propietaria marca la foto que muestra el tamaño real."""
    ids = _preparar(client, auth)
    assert _marcadas(_escala(client, auth, ids[1])) == [ids[1]]
    imagenes = client.get("/admin/productos/1", headers=auth).json()["imagenes"]
    assert [i["es_referencia_escala"] for i in imagenes] == [False, True, False]


def test_la_nueva_reemplaza_a_la_anterior(client, auth, bucket):
    """HU004 E3: nunca hay dos fotos de escala."""
    ids = _preparar(client, auth)
    _escala(client, auth, ids[0])
    assert _marcadas(_escala(client, auth, ids[2])) == [ids[2]]


def test_desmarcar(client, auth, bucket):
    ids = _preparar(client, auth)
    _escala(client, auth, ids[0])
    assert _marcadas(_escala(client, auth, ids[0], False)) == []
    # Desmarcar otra que no es la de escala no toca la marcada
    _escala(client, auth, ids[0])
    assert _marcadas(_escala(client, auth, ids[1], False)) == [ids[0]]


def test_imagen_de_otro_producto_o_inexistente_da_404(client, auth, bucket):
    """HU004 E4."""
    ids = _preparar(client, auth, fotos=1)
    client.post("/admin/productos", json={**COLLAR, "nombre": "Collar de cuarzo"}, headers=auth)
    assert _escala(client, auth, ids[0], producto_id=2).status_code == 404
    assert _escala(client, auth, 999).status_code == 404
    assert client.patch(f"{URL}/{ids[0]}/escala", json={}, headers=auth).status_code == 422
    assert _marcadas(client.patch(f"{URL}/{ids[0]}/escala", json={"es_referencia_escala": False},
                                  headers=auth)) == []


def test_eliminar_la_foto_de_escala_deja_el_producto_sin_ninguna(client, auth, bucket):
    """HU004 E5: no se asigna otra automáticamente."""
    ids = _preparar(client, auth)
    _escala(client, auth, ids[1])
    assert client.delete(f"{URL}/{ids[1]}", headers=auth).status_code == 204
    imagenes = client.get("/admin/productos/1", headers=auth).json()["imagenes"]
    assert len(imagenes) == 2 and not any(i["es_referencia_escala"] for i in imagenes)


def test_la_ficha_publica_expone_la_foto_de_escala(client, auth, bucket):
    """HU004 Esc.2: la clienta ve cuál es la foto de escala."""
    ids = _preparar(client, auth, fotos=2)
    _escala(client, auth, ids[1])
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    imagenes = client.get("/catalogo/1").json()["imagenes"]
    assert [i["es_referencia_escala"] for i in imagenes] == [False, True]
