"""T-07 (AKASH-148) y HU032: escenarios de error de productos, variantes y fotos (HU014, HU027, HU016, HU032, HU028)."""
import pytest
from sqlalchemy.orm import Session

from app import config
from app.services import storage
from tests.fabricas import crear_pedido, dar_stock

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
PULSERA = {
    "categoria_id": 2,
    "nombre": "Pulsera de cuarzo",
    "descripcion": "Pulsera de cuentas de cuarzo natural con hilo elástico.",
    "precio_base": "25.00",
}
VARIANTES = "/admin/productos/1/variantes"


def _crear(client, auth, **cambios):
    return client.post("/admin/productos", json={**PULSERA, **cambios}, headers=auth)


def _editar(client, auth, producto_id=1, **cambios):
    return client.put(f"/admin/productos/{producto_id}", json={**PULSERA, **cambios}, headers=auth)


def _variante(client, auth, nombre, **datos):
    return client.post(VARIANTES, json={"nombre": nombre, **datos}, headers=auth)


@pytest.fixture
def bucket(monkeypatch):
    archivos = {}
    monkeypatch.setattr(config, "SUPABASE_URL", "https://prueba.supabase.co")

    def subir(ruta, contenido, content_type):
        archivos[ruta] = contenido
        return storage.url_publica(ruta)

    monkeypatch.setattr(storage, "subir", subir)
    monkeypatch.setattr(storage, "borrar", lambda ruta: archivos.pop(ruta))
    return archivos


# --- HU014 E6: nombre duplicado dentro de la categoría ---

def test_nombre_duplicado_en_la_misma_categoria(client, auth):
    assert _crear(client, auth).status_code == 201
    respuesta = _crear(client, auth, nombre="  PULSERA de Cuarzo ")
    assert respuesta.status_code == 409
    assert "id 1" in respuesta.json()["detail"] and "Pulsera de cuarzo" in respuesta.json()["detail"]


def test_mismo_nombre_en_otra_categoria_si_se_permite(client, auth):
    assert _crear(client, auth).status_code == 201
    assert _crear(client, auth, categoria_id=3).status_code == 201


def test_editar_con_nombre_de_otro_producto_de_la_categoria(client, auth):
    _crear(client, auth)
    _crear(client, auth, nombre="Pulsera de amatista")
    assert _editar(client, auth, producto_id=2, nombre="pulsera de cuarzo").status_code == 409
    assert _editar(client, auth, producto_id=2, nombre="Pulsera de amatista").status_code == 200  # su propio nombre
    assert _editar(client, auth, producto_id=1, nombre="Pulsera de cuarzo", precio_base="30.00").status_code == 200


# --- HU014 E7 y E10: rangos y textos ---

@pytest.mark.parametrize("cambio", [
    {"precio_base": "10000.00"},
    {"precio_base": "0.00"},
    {"precio_base": "12.345"},
    {"descripcion": "x" * 1001},
    {"descripcion": "   "},
    {"medidas": "x" * 81},
    {"peso_g": "0"},
    {"peso_g": "-3"},
])
def test_rangos_y_textos_del_producto(client, auth, cambio):
    assert _crear(client, auth, **cambio).status_code == 422


def test_limites_exactos_del_producto(client, auth):
    respuesta = _crear(client, auth, precio_base="9999.99", descripcion="x" * 1000, medidas="x" * 80, peso_g="0.01")
    assert respuesta.status_code == 201
    assert respuesta.json()["precio_base"] == "9999.99"
    assert _crear(client, auth, nombre="Otra", precio_base="0.01").status_code == 201


def test_precio_propio_de_variante_fuera_de_rango(client, auth):
    _crear(client, auth)
    assert _variante(client, auth, "Amatista", precio="10000.00").status_code == 422
    assert _variante(client, auth, "Amatista", precio="0").status_code == 422
    assert _variante(client, auth, "Amatista", precio="9999.99").status_code == 201


# --- HU032 E10: edición simultánea ---

def test_edicion_simultanea_con_marca_vieja_responde_409(client, auth):
    _crear(client, auth)
    marca = client.get("/admin/productos/1", headers=auth).json()["actualizado_en"]
    assert marca
    primera = _editar(client, auth, precio_base="26.00", actualizado_en=marca)
    assert primera.status_code == 200
    assert primera.json()["actualizado_en"] != marca
    segunda = _editar(client, auth, precio_base="27.00", actualizado_en=marca)  # la otra pestaña
    assert segunda.status_code == 409
    assert "Otra persona modificó este producto" in segunda.json()["detail"]
    assert client.get("/admin/productos/1", headers=auth).json()["precio_base"] == "26.00"
    # Con la marca nueva sí guarda
    assert _editar(client, auth, precio_base="27.00", actualizado_en=primera.json()["actualizado_en"]).status_code == 200


def test_sin_marca_no_se_valida(client, auth):
    _crear(client, auth)
    assert _editar(client, auth, precio_base="26.00").status_code == 200
    assert _editar(client, auth, precio_base="27.00").status_code == 200


def test_cambios_en_variantes_fotos_y_publicacion_renuevan_la_marca(client, auth, bucket):
    _crear(client, auth)

    def marca():
        return client.get("/admin/productos/1", headers=auth).json()["actualizado_en"]

    anterior = marca()
    for accion in (
        lambda: _variante(client, auth, "Amatista"),
        lambda: client.put(f"{VARIANTES}/2", json={"nombre": "Amatista lila"}, headers=auth),
        lambda: client.post("/admin/productos/1/imagenes", files={"foto": ("f.jpg", JPG, "image/jpeg")}, headers=auth),
        lambda: client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth),
        lambda: client.delete(f"{VARIANTES}/2", headers=auth),
    ):
        assert accion().status_code in (200, 201, 204)
        actual = marca()
        assert actual != anterior
        anterior = actual
    # Publicar otra vez no cambia nada (HU016 E7)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    assert marca() == anterior


# --- HU014 E8: no dejar sin foto un producto publicado ---

def test_no_se_borra_la_unica_foto_de_un_producto_publicado(client, auth, bucket, monkeypatch):
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", True)
    _crear(client, auth)
    foto = client.post("/admin/productos/1/imagenes", files={"foto": ("f.jpg", JPG, "image/jpeg")},
                       headers=auth).json()["id"]
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    respuesta = client.delete(f"/admin/productos/1/imagenes/{foto}", headers=auth)
    assert respuesta.status_code == 409
    assert "única foto" in respuesta.json()["detail"]
    # Con otra foto sí se puede
    client.post("/admin/productos/1/imagenes", files={"foto": ("g.jpg", JPG, "image/jpeg")}, headers=auth)
    assert client.delete(f"/admin/productos/1/imagenes/{foto}", headers=auth).status_code == 204


def test_sin_la_regla_o_despublicado_se_puede_borrar_la_ultima_foto(client, auth, bucket, monkeypatch):
    _crear(client, auth)
    subir = lambda: client.post("/admin/productos/1/imagenes", files={"foto": ("f.jpg", JPG, "image/jpeg")},  # noqa: E731
                                headers=auth).json()["id"]
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", False)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    assert client.delete(f"/admin/productos/1/imagenes/{subir()}", headers=auth).status_code == 204
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", True)
    client.patch("/admin/productos/1/publicado", json={"publicado": False}, headers=auth)
    assert client.delete(f"/admin/productos/1/imagenes/{subir()}", headers=auth).status_code == 204


# --- HU027 E5: variante duplicada ---

def test_variante_con_nombre_repetido_en_el_producto(client, auth):
    _crear(client, auth)
    assert _variante(client, auth, "Amatista").status_code == 201
    respuesta = _variante(client, auth, " AMATISTA ")
    assert respuesta.status_code == 409
    assert "Amatista" in respuesta.json()["detail"]
    assert client.put(f"{VARIANTES}/1", json={"nombre": "amatista"}, headers=auth).status_code == 409
    assert client.put(f"{VARIANTES}/2", json={"nombre": "Amatista", "precio": "30.00"}, headers=auth).status_code == 200


def test_mismo_nombre_de_variante_en_otro_producto_si_se_permite(client, auth):
    _crear(client, auth)
    _crear(client, auth, nombre="Pulsera de ónix")
    assert _variante(client, auth, "Amatista").status_code == 201
    assert client.post("/admin/productos/2/variantes", json={"nombre": "Amatista"}, headers=auth).status_code == 201


# --- HU027 E10: máximo 30 variantes activas ---

def test_maximo_30_variantes_activas(client, auth, engine):
    _crear(client, auth)  # nace con "Única"
    for n in range(2, 31):
        assert _variante(client, auth, f"Piedra {n}").status_code == 201
    respuesta = _variante(client, auth, "Piedra 31")
    assert respuesta.status_code == 422
    assert "30 variantes activas" in respuesta.json()["detail"]
    # Retirar una con historial libera un cupo, pero reactivarla con 30 activas vuelve a fallar.
    with Session(engine) as db:
        crear_pedido(db, "AK-0001", [(2, 1, "25.00")])
    assert client.delete(f"{VARIANTES}/2", headers=auth).json()["desactivada"] is True
    assert _variante(client, auth, "Piedra 31").status_code == 201
    reactivar = client.put(f"{VARIANTES}/2", json={"nombre": "Piedra 2", "activa": True}, headers=auth)
    assert reactivar.status_code == 422


# --- HU027 E9 / HU032 E8: variante con historial se desactiva ---

def test_variante_con_movimientos_se_desactiva_y_conserva_su_historial(client, auth):
    _crear(client, auth)
    vid = _variante(client, auth, "Amatista").json()["id"]
    dar_stock(client, auth, vid, 3)
    respuesta = client.delete(f"{VARIANTES}/{vid}", headers=auth)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["desactivada"] is True
    assert cuerpo["variante"]["activa"] is False
    assert cuerpo["variante"]["existencias"] == 3
    assert len(client.get(f"/admin/variantes/{vid}/movimientos", headers=auth).json()) == 1
    variantes = client.get(VARIANTES, headers=auth).json()
    assert [(v["nombre"], v["activa"]) for v in variantes] == [("Única", True), ("Amatista", False)]
    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert (fila["num_variantes"], fila["existencias_total"]) == (1, 0)


def test_reactivar_una_variante(client, auth):
    _crear(client, auth)
    vid = _variante(client, auth, "Amatista").json()["id"]
    dar_stock(client, auth, vid, 1)
    client.delete(f"{VARIANTES}/{vid}", headers=auth)
    duplicada = _variante(client, auth, "amatista")
    assert duplicada.status_code == 409
    assert "reactívala" in duplicada.json()["detail"]
    respuesta = client.put(f"{VARIANTES}/{vid}", json={"nombre": "Amatista", "activa": True}, headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["activa"] is True


def test_sin_activa_en_el_put_no_cambia_el_estado(client, auth):
    _crear(client, auth)
    vid = _variante(client, auth, "Amatista").json()["id"]
    client.put(f"{VARIANTES}/{vid}", json={"nombre": "Amatista", "activa": False}, headers=auth)
    assert client.put(f"{VARIANTES}/{vid}", json={"nombre": "Amatista lila"}, headers=auth).json()["activa"] is False


def test_no_se_desactiva_la_ultima_variante_activa(client, auth):
    _crear(client, auth)
    dar_stock(client, auth, 1, 2)
    assert client.delete(f"{VARIANTES}/1", headers=auth).status_code == 409
    respuesta = client.put(f"{VARIANTES}/1", json={"nombre": "Única", "activa": False}, headers=auth)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El producto debe conservar al menos una variante activa"


def test_variante_sin_historial_se_borra_como_antes(client, auth):
    _crear(client, auth)
    vid = _variante(client, auth, "Amatista").json()["id"]
    assert client.delete(f"{VARIANTES}/{vid}", headers=auth).status_code == 204
    assert client.delete(f"{VARIANTES}/{vid}", headers=auth).status_code == 404


# --- HU016: publicar exige una variante ACTIVA ---

def test_publicar_exige_una_variante_activa(client, auth, engine):
    from app.models.variante import Variante
    _crear(client, auth)
    with Session(engine) as db:  # caso defensivo: datos cambiados por fuera de la API
        db.query(Variante).update({"activa": False})
        db.commit()
    respuesta = client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "No se puede publicar: falta al menos una variante activa"


def test_publicar_producto_inexistente_y_cuerpo_invalido(client, auth):
    assert client.patch("/admin/productos/99/publicado", json={"publicado": True}, headers=auth).status_code == 404
    _crear(client, auth)
    assert client.patch("/admin/productos/1/publicado", json={"publicado": "tal vez"}, headers=auth).status_code == 422


# --- HU028 E8: variante retirada en el carrito ---

def test_variante_retirada_no_se_puede_comprar(client, auth):
    _crear(client, auth)
    vid = _variante(client, auth, "Amatista").json()["id"]
    dar_stock(client, auth, 1, 2)
    dar_stock(client, auth, vid, 2)
    client.patch("/admin/productos/1/publicado", json={"publicado": True}, headers=auth)
    client.delete(f"{VARIANTES}/{vid}", headers=auth)
    respuesta = client.post("/carrito/validar", json={"items": [{"variante_id": 1, "cantidad": 1},
                                                                {"variante_id": vid, "cantidad": 1}]})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is False
    retirada = cuerpo["items"][1]
    assert (retirada["estado"], retirada["cantidad_maxima"]) == ("no_disponible", 0)
    assert retirada["mensaje"] == "Esta variante ya no está disponible; quítala del pedido"
    assert cuerpo["items"][0]["estado"] == "ok"
