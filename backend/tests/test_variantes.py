from sqlalchemy import text

PULSERA = {
    "categoria_id": 2,
    "nombre": "Pulsera de cuarzo",
    "descripcion": "Pulsera de cuentas de cuarzo natural con hilo elástico.",
    "precio_base": "25.00",
}
URL = "/admin/productos/1/variantes"


def _producto(client, auth):
    assert client.post("/admin/productos", json=PULSERA, headers=auth).status_code == 201


def _variante(client, auth, **datos):
    return client.post(URL, json={"nombre": "Cuarzo rosa", "existencias": 3, **datos}, headers=auth)


def test_rutas_de_variantes_exigen_token(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={"nombre": "Amatista"}).status_code == 401
    assert client.put(f"{URL}/1", json={"nombre": "Amatista"}).status_code == 401
    assert client.delete(f"{URL}/1").status_code == 401


def test_crear_variante_hereda_precio_del_producto(client, auth):
    _producto(client, auth)
    respuesta = _variante(client, auth, propiedades="Amor propio y armonía")
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["producto_id"] == 1
    assert cuerpo["precio"] is None
    assert cuerpo["precio_efectivo"] == "25.00"
    assert cuerpo["existencias"] == 3
    assert cuerpo["propiedades"] == "Amor propio y armonía"


def test_variante_con_precio_propio(client, auth):
    _producto(client, auth)
    respuesta = _variante(client, auth, nombre="Labradorita", precio="32.00")
    assert respuesta.json()["precio"] == "32.00"
    assert respuesta.json()["precio_efectivo"] == "32.00"


def test_variante_sigue_al_precio_base_si_cambia(client, auth):
    _producto(client, auth)
    _variante(client, auth)
    client.put("/admin/productos/1", json={**PULSERA, "precio_base": "28.00"}, headers=auth)
    assert client.get(URL, headers=auth).json()[0]["precio_efectivo"] == "28.00"


def test_doce_piedras_de_la_pulsera(client, auth):
    _producto(client, auth)
    piedras = ["Cuarzo rosa", "Ojo de tigre", "Pirita", "Turmalina negra", "Amatista", "Citrino",
               "Jade", "Howlita", "Piedra luna", "Lapislázuli", "Cuarzo ahumado", "Labradorita"]
    for piedra in piedras:
        assert _variante(client, auth, nombre=piedra).status_code == 201
    assert [v["nombre"] for v in client.get(URL, headers=auth).json()] == piedras
    fila = client.get("/admin/productos", headers=auth).json()[0]
    assert fila["num_variantes"] == 12
    assert fila["existencias_total"] == 36


def test_validaciones_de_variante(client, auth):
    _producto(client, auth)
    assert client.post(URL, json={}, headers=auth).status_code == 422
    assert _variante(client, auth, nombre="  ").status_code == 422
    assert _variante(client, auth, nombre="x" * 81).status_code == 422
    assert _variante(client, auth, existencias=-1).status_code == 422
    assert _variante(client, auth, precio="0").status_code == 422
    assert _variante(client, auth, precio="-3").status_code == 422


def test_existencias_por_defecto_cero(client, auth):
    _producto(client, auth)
    assert client.post(URL, json={"nombre": "Pirita"}, headers=auth).json()["existencias"] == 0


def test_producto_inexistente(client, auth):
    assert client.get("/admin/productos/99/variantes", headers=auth).status_code == 404
    assert client.post("/admin/productos/99/variantes", json={"nombre": "Pirita"}, headers=auth).status_code == 404


def test_actualizar_variante(client, auth):
    _producto(client, auth)
    _variante(client, auth, precio="30.00")
    respuesta = client.put(f"{URL}/1", json={"nombre": "Cuarzo rosa", "precio": None, "existencias": 5}, headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["precio"] is None
    assert respuesta.json()["precio_efectivo"] == "25.00"
    assert respuesta.json()["existencias"] == 5


def test_variante_de_otro_producto_no_se_toca(client, auth):
    _producto(client, auth)
    client.post("/admin/productos", json={**PULSERA, "nombre": "Roll-on", "categoria_id": 5}, headers=auth)
    client.post("/admin/productos/2/variantes", json={"nombre": "Citrino"}, headers=auth)
    assert client.put(f"{URL}/1", json={"nombre": "Otro"}, headers=auth).status_code == 404
    assert client.delete(f"{URL}/1", headers=auth).status_code == 404
    assert client.get("/admin/productos/2/variantes", headers=auth).json()[0]["nombre"] == "Citrino"


def test_eliminar_variante(client, auth):
    _producto(client, auth)
    _variante(client, auth)
    assert client.delete(f"{URL}/1", headers=auth).status_code == 204
    assert client.get(URL, headers=auth).json() == []
    assert client.delete(f"{URL}/1", headers=auth).status_code == 404


def test_no_se_elimina_variante_con_pedidos(client, auth, engine):
    _producto(client, auth)
    _variante(client, auth)
    # Tabla mínima con la misma FK que detalle_pedido en Supabase (sin ON DELETE).
    with engine.begin() as conexion:
        conexion.execute(text(
            "CREATE TABLE detalle_pedido (id INTEGER PRIMARY KEY, variante_id INTEGER NOT NULL REFERENCES variante(id))"
        ))
        conexion.execute(text("INSERT INTO detalle_pedido (variante_id) VALUES (1)"))
    respuesta = client.delete(f"{URL}/1", headers=auth)
    assert respuesta.status_code == 409
    assert len(client.get(URL, headers=auth).json()) == 1
