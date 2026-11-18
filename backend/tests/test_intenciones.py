"""HU008 (AKASH-180): asignar intenciones a cada piedra y filtrar el catálogo por intención.
HU005 (AKASH-168): intenciones en la ficha del producto. Datos ficticios."""
import pytest
from sqlalchemy import text

from tests.fabricas import crear_intenciones, dar_stock

NOMBRES = ["Protección", "Calma y paz interior", "Abundancia y prosperidad", "Claridad mental",
           "Comunicación", "Buena suerte", "Energía y vitalidad"]
PULSERA = {
    "categoria_id": 2,
    "nombre": "Pulsera de cuarzo",
    "descripcion": "Pulsera de cuentas de piedra natural con hilo elástico.",
    "precio_base": "35.00",
    "es_pieza_natural": True,
}
ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural.",
    "precio_base": "45.00",
}
SPRAY = {
    "categoria_id": 6,
    "nombre": "Spray áurico",
    "descripcion": "Spray de 60 ml con agua floral.",
    "precio_base": "25.00",
}


@pytest.fixture
def ids(engine):
    return crear_intenciones(engine, NOMBRES + ["Intuición (retirada)"], inactivas=("Intuición (retirada)",))


def _producto(client, auth, datos, piedras=None, publicar=True):
    """Crea el producto; `piedras` renombra la "Única" con la primera y agrega las demás. Devuelve (id, [variante_ids])."""
    pid = client.post("/admin/productos", json=datos, headers=auth).json()["id"]
    variantes = [client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]]
    if piedras:
        client.put(f"/admin/productos/{pid}/variantes/{variantes[0]}", json={"nombre": piedras[0]}, headers=auth)
        for nombre in piedras[1:]:
            variantes.append(client.post(f"/admin/productos/{pid}/variantes", json={"nombre": nombre},
                                         headers=auth).json()["id"])
    for vid in variantes:
        dar_stock(client, auth, vid, 2)
    if publicar:
        assert client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth).status_code == 200
    return pid, variantes


def _asignar(client, auth, variante_id, intencion_ids):
    return client.put(f"/admin/variantes/{variante_id}/intenciones", json={"intencion_ids": intencion_ids}, headers=auth)


def _nombres(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return [p["nombre"] for p in respuesta.json()]


# ---------- Panel ----------

def test_rutas_del_panel_exigen_token(client):
    assert client.get("/admin/intenciones").status_code == 401
    assert client.put("/admin/variantes/1/intenciones", json={"intencion_ids": []}).status_code == 401


def test_lista_activas_e_inactivas_por_nombre(client, auth, ids):
    lista = client.get("/admin/intenciones", headers=auth).json()
    assert [i["nombre"] for i in lista] == sorted(NOMBRES + ["Intuición (retirada)"])
    retirada = next(i for i in lista if i["nombre"] == "Intuición (retirada)")
    assert retirada == {"id": ids["Intuición (retirada)"], "nombre": "Intuición (retirada)", "activa": False}


def test_asignar_reemplaza_el_conjunto_y_se_ve_en_la_variante(client, auth, ids):
    """HU008 Esc.1: la propietaria marca las intenciones de la piedra y quedan guardadas."""
    pid, (amatista,) = _producto(client, auth, PULSERA, ["Amatista"])
    respuesta = _asignar(client, auth, amatista, [ids["Protección"], ids["Calma y paz interior"]])
    assert respuesta.status_code == 200
    assert respuesta.json() == [{"id": ids["Calma y paz interior"], "nombre": "Calma y paz interior"},
                                {"id": ids["Protección"], "nombre": "Protección"}]
    variante = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]
    assert [i["nombre"] for i in variante["intenciones"]] == ["Calma y paz interior", "Protección"]

    # Reemplaza (no suma): ahora solo Claridad mental
    assert _asignar(client, auth, amatista, [ids["Claridad mental"]]).json() == [
        {"id": ids["Claridad mental"], "nombre": "Claridad mental"}]
    # Lista vacía = sin intenciones
    assert _asignar(client, auth, amatista, []).json() == []
    assert client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["intenciones"] == []


def test_repetidas_se_guardan_una_vez(client, auth, ids, engine):
    """HU008 E5."""
    _, (amatista,) = _producto(client, auth, PULSERA, ["Amatista"])
    p = ids["Protección"]
    assert _asignar(client, auth, amatista, [p, p, p]).json() == [{"id": p, "nombre": "Protección"}]
    with engine.connect() as conexion:
        assert conexion.execute(text("SELECT count(*) FROM variante_intencion")).scalar() == 1


def test_maximo_5_intenciones(client, auth, ids):
    """HU008 E6: 6 distintas → 422; 5 distintas (aunque lleguen 7 con repetidas) se aceptan."""
    _, (amatista,) = _producto(client, auth, PULSERA, ["Amatista"])
    seis = [ids[n] for n in NOMBRES[:6]]
    respuesta = _asignar(client, auth, amatista, seis)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "Máximo 5 intenciones por piedra"
    cinco = [ids[n] for n in NOMBRES[:5]]
    assert len(_asignar(client, auth, amatista, cinco + cinco[:2]).json()) == 5


def test_intencion_inexistente_o_desactivada(client, auth, ids):
    """HU008 E4: 422 indicando cuál; no se guarda nada."""
    _, (amatista,) = _producto(client, auth, PULSERA, ["Amatista"])
    _asignar(client, auth, amatista, [ids["Protección"]])
    respuesta = _asignar(client, auth, amatista, [ids["Protección"], 999])
    assert (respuesta.status_code, respuesta.json()["detail"]) == (422, "La intención 999 no existe")
    respuesta = _asignar(client, auth, amatista, [ids["Intuición (retirada)"]])
    assert respuesta.status_code == 422
    assert "Intuición (retirada)" in respuesta.json()["detail"] and "desactivada" in respuesta.json()["detail"]
    assert _asignar(client, auth, amatista, [ids["Protección"]]).status_code == 200  # lo anterior seguía igual


def test_variante_inexistente_y_cuerpo_invalido(client, auth, ids):
    assert _asignar(client, auth, 999, [ids["Protección"]]).status_code == 404
    _, (amatista,) = _producto(client, auth, PULSERA, ["Amatista"])
    assert client.put(f"/admin/variantes/{amatista}/intenciones", json={}, headers=auth).status_code == 422
    assert client.put(f"/admin/variantes/{amatista}/intenciones", json={"intencion_ids": ["x"]},
                      headers=auth).status_code == 422


def test_borrar_la_variante_borra_sus_intenciones(client, auth, ids, engine):
    pid, (amatista, citrino) = _producto(client, auth, PULSERA, ["Amatista", "Citrino"], publicar=False)
    # Sin historial: para poder borrarla, se crea otra sin stock
    jade = client.post(f"/admin/productos/{pid}/variantes", json={"nombre": "Jade"}, headers=auth).json()["id"]
    _asignar(client, auth, jade, [ids["Buena suerte"]])
    assert client.delete(f"/admin/productos/{pid}/variantes/{jade}", headers=auth).status_code == 204
    with engine.connect() as conexion:
        assert conexion.execute(text("SELECT count(*) FROM variante_intencion")).scalar() == 0


# ---------- Catálogo: filtro por intención ----------

@pytest.fixture
def tienda(client, auth, ids):
    """Pulsera (Amatista: Protección; Citrino: Abundancia), Anillo (Turmalina: Protección), Spray sin intenciones."""
    _, (amatista, citrino) = _producto(client, auth, PULSERA, ["Amatista", "Citrino"])
    _, (turmalina,) = _producto(client, auth, ANILLO, ["Turmalina negra"])
    _producto(client, auth, SPRAY)
    _asignar(client, auth, amatista, [ids["Protección"], ids["Calma y paz interior"]])
    _asignar(client, auth, citrino, [ids["Abundancia y prosperidad"]])
    _asignar(client, auth, turmalina, [ids["Protección"]])
    return {"amatista": amatista, "citrino": citrino, "turmalina": turmalina}


def test_filtrar_por_intencion(client, ids, tienda):
    """HU008 Esc.2."""
    assert _nombres(client.get("/catalogo", params={"intencion_id": ids["Protección"]})) == [
        "Pulsera de cuarzo", "Anillo de plata con piedra"]
    assert _nombres(client.get("/catalogo", params={"intencion_id": ids["Abundancia y prosperidad"]})) == [
        "Pulsera de cuarzo"]


def test_filtro_combinado_con_categoria(client, ids, tienda):
    """HU008 Esc.3: Protección + Anillos."""
    assert _nombres(client.get("/catalogo", params={"intencion_id": ids["Protección"], "categoria_id": 4})) == [
        "Anillo de plata con piedra"]


def test_productos_sin_intenciones_siguen_en_el_catalogo_general(client, ids, tienda):
    """HU008 E8."""
    assert "Spray áurico" in _nombres(client.get("/catalogo"))
    assert "Spray áurico" not in _nombres(client.get("/catalogo", params={"intencion_id": ids["Protección"]}))


def test_intencion_inexistente_o_desactivada_da_lista_vacia(client, ids, tienda):
    assert _nombres(client.get("/catalogo", params={"intencion_id": 999})) == []
    assert _nombres(client.get("/catalogo", params={"intencion_id": ids["Intuición (retirada)"]})) == []
    assert client.get("/catalogo", params={"intencion_id": "protección"}).status_code == 422


def test_desactivar_la_intencion_la_saca_del_filtro(client, engine, ids, tienda):
    with engine.begin() as conexion:
        conexion.execute(text("UPDATE intencion SET activa = 0 WHERE id = :id"), {"id": ids["Protección"]})
    assert _nombres(client.get("/catalogo", params={"intencion_id": ids["Protección"]})) == []


def test_variante_retirada_no_cuenta_para_el_filtro(client, auth, ids, tienda):
    """Solo cuentan las piedras activas (HU028 E8): si se retira la Turmalina, el anillo sale del filtro."""
    anillo = client.get("/catalogo", params={"categoria_id": 4}).json()[0]["id"]
    client.post(f"/admin/productos/{anillo}/variantes", json={"nombre": "Ónix"}, headers=auth)
    client.put(f"/admin/productos/{anillo}/variantes/{tienda['turmalina']}",
               json={"nombre": "Turmalina negra", "activa": False}, headers=auth)
    assert _nombres(client.get("/catalogo", params={"intencion_id": ids["Protección"]})) == ["Pulsera de cuarzo"]


def test_intenciones_del_catalogo_con_conteo(client, auth, ids, tienda):
    """HU008: para el filtro y para las sugerencias de E7 (las que tienen productos > 0)."""
    lista = client.get("/catalogo/intenciones").json()
    assert [i["nombre"] for i in lista] == sorted(NOMBRES)  # la desactivada no sale
    conteo = {i["nombre"]: i["productos"] for i in lista}
    assert conteo["Protección"] == 2
    assert conteo["Abundancia y prosperidad"] == 1
    assert conteo["Comunicación"] == 0
    # Un producto despublicado deja de contar
    anillo = client.get("/catalogo", params={"categoria_id": 4}).json()[0]["id"]
    client.patch(f"/admin/productos/{anillo}/publicado", json={"publicado": False}, headers=auth)
    assert {i["nombre"]: i["productos"] for i in client.get("/catalogo/intenciones").json()}["Protección"] == 1


def test_intencion_desactivada_deja_de_salir_en_el_panel(client, auth, engine, ids, tienda):
    """La asignación se conserva en la base, pero la variante del panel solo muestra las activas."""
    with engine.begin() as conexion:
        conexion.execute(text("UPDATE intencion SET activa = 0 WHERE id = :id"), {"id": ids["Calma y paz interior"]})
    pulsera = client.get("/catalogo", params={"categoria_id": 2}).json()[0]["id"]
    panel = client.get(f"/admin/productos/{pulsera}/variantes", headers=auth).json()
    assert [i["nombre"] for i in panel[0]["intenciones"]] == ["Protección"]
