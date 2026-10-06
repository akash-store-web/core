from sqlalchemy.orm import Session

from app import config

from app.models.imagen import Imagen
from app.models.producto import Producto
from app.models.variante import Variante

PULSERA = {
    "categoria_id": 2,
    "nombre": "Pulsera de cuarzo",
    "descripcion": "Pulsera de cuentas de cuarzo natural con hilo elástico.",
    "precio_base": "25.00",
    "material": "Cuarzo natural",
    "medidas": "Cuentas de 8 mm",
    "es_pieza_natural": True,
}


def _crear(client, auth, **cambios):
    return client.post("/admin/productos", json={**PULSERA, **cambios}, headers=auth)


# --- Protección del panel ---

def test_rutas_admin_exigen_token(client):
    assert client.get("/admin/productos").status_code == 401
    assert client.post("/admin/productos", json=PULSERA).status_code == 401
    assert client.put("/admin/productos/1", json=PULSERA).status_code == 401
    assert client.get("/admin/categorias").status_code == 401


def test_listar_categorias_en_orden(client, auth):
    respuesta = client.get("/admin/categorias", headers=auth)
    assert respuesta.status_code == 200
    assert [c["nombre"] for c in respuesta.json()][:2] == ["Boxes y kits", "Pulseras"]
    assert len(respuesta.json()) == 7


# --- POST /admin/productos ---

def test_crear_producto_completo(client, auth):
    respuesta = _crear(client, auth)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] == 1
    assert cuerpo["nombre"] == "Pulsera de cuarzo"
    assert cuerpo["precio_base"] == "25.00"
    assert cuerpo["es_pieza_natural"] is True
    assert cuerpo["publicado"] is False  # se crea despublicado; se publica en HU016
    assert cuerpo["imagenes"] == []


def test_crear_producto_solo_con_campos_obligatorios(client, auth):
    datos = {k: PULSERA[k] for k in ("categoria_id", "nombre", "descripcion", "precio_base")}
    respuesta = client.post("/admin/productos", json=datos, headers=auth)
    assert respuesta.status_code == 201
    assert respuesta.json()["material"] is None
    assert respuesta.json()["es_pieza_natural"] is False


def test_producto_sin_variantes_nace_con_variante_unica(client, auth):
    """HU027 #3: un producto sin variantes funciona con una única existencia."""
    _crear(client, auth, existencias=4)
    variantes = client.get("/admin/productos/1/variantes", headers=auth).json()
    assert [(v["nombre"], v["existencias"], v["precio"]) for v in variantes] == [("Única", 4, None)]
    assert variantes[0]["precio_efectivo"] == "25.00"
    assert client.get("/admin/productos", headers=auth).json()[0]["existencias_total"] == 4


def test_existencias_iniciales_por_defecto_y_negativas(client, auth):
    _crear(client, auth)
    assert client.get("/admin/productos", headers=auth).json()[0]["existencias_total"] == 0
    assert _crear(client, auth, existencias=-1).status_code == 422


def test_crear_producto_ignora_publicado(client, auth):
    assert _crear(client, auth, publicado=True).json()["publicado"] is False


def test_campos_obligatorios_vacios(client, auth):
    for campo in ("categoria_id", "nombre", "descripcion", "precio_base"):
        datos = {k: v for k, v in PULSERA.items() if k != campo}
        respuesta = client.post("/admin/productos", json=datos, headers=auth)
        assert respuesta.status_code == 422, campo


def test_nombre_y_descripcion_en_blanco(client, auth):
    assert _crear(client, auth, nombre="   ").status_code == 422
    assert _crear(client, auth, descripcion="").status_code == 422


def test_precio_invalido(client, auth):
    assert _crear(client, auth, precio_base="0").status_code == 422
    assert _crear(client, auth, precio_base="-5").status_code == 422
    assert _crear(client, auth, precio_base="25.999").status_code == 422
    assert _crear(client, auth, precio_base="abc").status_code == 422


def test_textos_demasiado_largos(client, auth):
    assert _crear(client, auth, nombre="x" * 121).status_code == 422
    assert _crear(client, auth, material="x" * 81).status_code == 422


def test_categoria_inexistente(client, auth):
    respuesta = _crear(client, auth, categoria_id=99)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "La categoría no existe"


# --- PUT /admin/productos/{id} ---

def test_actualizar_producto(client, auth):
    _crear(client, auth)
    datos = {**PULSERA, "precio_base": "30.00", "categoria_id": 3, "material": None}
    respuesta = client.put("/admin/productos/1", json=datos, headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json()["precio_base"] == "30.00"
    assert respuesta.json()["categoria_id"] == 3
    assert respuesta.json()["material"] is None
    assert client.get("/admin/productos/1", headers=auth).json()["precio_base"] == "30.00"


def test_actualizar_no_cambia_publicado(client, auth, engine):
    _crear(client, auth)
    with Session(engine) as db:
        db.get(Producto, 1).publicado = True
        db.commit()
    respuesta = client.put("/admin/productos/1", json={**PULSERA, "publicado": False}, headers=auth)
    assert respuesta.json()["publicado"] is True


def test_actualizar_producto_inexistente(client, auth):
    assert client.put("/admin/productos/99", json=PULSERA, headers=auth).status_code == 404


def test_actualizar_con_datos_invalidos(client, auth):
    _crear(client, auth)
    assert client.put("/admin/productos/1", json={**PULSERA, "precio_base": "-1"}, headers=auth).status_code == 422
    assert client.put("/admin/productos/1", json={**PULSERA, "categoria_id": 99}, headers=auth).status_code == 422


# --- GET /admin/productos ---

def test_obtener_producto_inexistente(client, auth):
    assert client.get("/admin/productos/99", headers=auth).status_code == 404


def test_listado_vacio(client, auth):
    respuesta = client.get("/admin/productos", headers=auth)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listado_con_resumen_de_variantes_y_foto(client, auth, engine):
    _crear(client, auth)
    _crear(client, auth, nombre="Roll-on de amatista", categoria_id=5, precio_base="35.00")
    with Session(engine) as db:
        db.add_all([
            Variante(producto_id=1, nombre="Cuarzo rosa", existencias=3),
            Variante(producto_id=1, nombre="Amatista", existencias=2),
            Imagen(producto_id=1, url="https://ejemplo/secundaria.jpg", orden=0),
            Imagen(producto_id=1, url="https://ejemplo/principal.jpg", orden=1, es_principal=True),
        ])
        db.commit()

    filas = client.get("/admin/productos", headers=auth).json()
    assert [f["nombre"] for f in filas] == ["Pulsera de cuarzo", "Roll-on de amatista"]
    pulsera, roll_on = filas
    assert pulsera["categoria"] == "Pulseras"
    assert pulsera["num_variantes"] == 3  # "Única" (0) + Cuarzo rosa (3) + Amatista (2)
    assert pulsera["existencias_total"] == 5
    assert pulsera["foto_principal"] == "https://ejemplo/principal.jpg"
    assert roll_on["num_variantes"] == 1
    assert (roll_on["foto_principal"], roll_on["foto_generica"]) == (config.FOTO_GENERICA_URL, True)
    assert pulsera["foto_generica"] is False


def test_busqueda_por_nombre_sin_distinguir_mayusculas(client, auth):
    _crear(client, auth)
    _crear(client, auth, nombre="Roll-on de amatista", categoria_id=5)
    filas = client.get("/admin/productos", params={"q": "PULSERA"}, headers=auth).json()
    assert [f["nombre"] for f in filas] == ["Pulsera de cuarzo"]


def test_filtro_por_categoria(client, auth):
    _crear(client, auth)
    _crear(client, auth, nombre="Roll-on de amatista", categoria_id=5)
    filas = client.get("/admin/productos", params={"categoria_id": 5}, headers=auth).json()
    assert [f["nombre"] for f in filas] == ["Roll-on de amatista"]
