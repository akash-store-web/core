"""HU007 (AKASH-175): filtro por rango de precio en GET /catalogo. Datos ficticios."""
import pytest

from tests.fabricas import crear_intenciones, dar_stock

URL = "/catalogo"


def _producto(client, auth, nombre, categoria_id, precio_base, piedras=(), stock=2):
    """piedras: [(nombre, precio | None, stock)]; sin piedras, la variante "Única" con `stock`."""
    pid = client.post("/admin/productos", json={
        "categoria_id": categoria_id, "nombre": nombre, "descripcion": f"{nombre} de prueba.",
        "precio_base": precio_base}, headers=auth).json()["id"]
    unica = client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]
    ids = []
    if piedras:
        (n0, p0, s0), *resto = piedras
        client.put(f"/admin/productos/{pid}/variantes/{unica}", json={"nombre": n0, "precio": p0}, headers=auth)
        ids.append((unica, s0))
        for n, p, s in resto:
            ids.append((client.post(f"/admin/productos/{pid}/variantes", json={"nombre": n, "precio": p},
                                    headers=auth).json()["id"], s))
    else:
        ids.append((unica, stock))
    for vid, s in ids:
        if s:
            dar_stock(client, auth, vid, s)
    assert client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth).status_code == 200
    return pid, [v for v, _ in ids]


@pytest.fixture
def tienda(client, auth):
    """Anillo: Amatista 40 y Turmalina 45 · Pulsera 30 · Spray 25 · Collar 60 (agotado)."""
    anillo, variantes = _producto(client, auth, "Anillo con piedra", 4, "45.00",
                                  [("Amatista", "40.00", 2), ("Turmalina negra", None, 2)])
    _producto(client, auth, "Pulsera de cuarzo", 2, "30.00")
    _producto(client, auth, "Spray áurico", 6, "25.00")
    _producto(client, auth, "Collar de jade", 3, "60.00", stock=0)
    return {"anillo": anillo, "amatista": variantes[0], "turmalina": variantes[1]}


def _nombres(client, **params):
    respuesta = client.get(URL, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return sorted(p["nombre"] for p in respuesta.json())


def test_filtra_por_rango_de_precio(client, tienda):
    """HU007 Esc.1: límites incluidos."""
    assert _nombres(client, precio_min="25", precio_max="30") == ["Pulsera de cuarzo", "Spray áurico"]
    assert _nombres(client, precio_min="30.00", precio_max="30.00") == ["Pulsera de cuarzo"]


def test_basta_una_variante_en_el_rango(client, tienda):
    """HU007 E8: variantes de 40 y 45, máximo 42 → el anillo aparece."""
    assert _nombres(client, precio_max="42") == ["Anillo con piedra", "Pulsera de cuarzo", "Spray áurico"]
    assert _nombres(client, precio_min="44", precio_max="50") == ["Anillo con piedra"]


def test_solo_un_limite_deja_el_otro_abierto(client, tienda):
    """HU007 E6."""
    assert _nombres(client, precio_min="45") == ["Anillo con piedra", "Collar de jade"]
    assert _nombres(client, precio_max="25") == ["Spray áurico"]
    assert _nombres(client, precio_min="0") == _nombres(client)


def test_minimo_mayor_que_maximo(client, tienda):
    """HU007 E4."""
    respuesta = client.get(URL, params={"precio_min": "50", "precio_max": "20"})
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "El precio mínimo no puede ser mayor que el máximo"


@pytest.mark.parametrize("params", [
    {"precio_min": "-1"}, {"precio_max": "-0.01"}, {"precio_max": "10000"}, {"precio_min": "abc"},
    {"precio_max": "12.345"}, {"precio_min": "NaN"},
])
def test_valores_invalidos_dan_422(client, tienda, params):
    """HU007 E5: negativos, > 9999.99, texto o más de 2 decimales."""
    assert client.get(URL, params=params).status_code == 422


def test_sin_resultados_da_lista_vacia(client, tienda):
    assert _nombres(client, precio_min="100", precio_max="200") == []


def test_categoria_inexistente_se_ignora(client, tienda):
    """HU007 E7: sin error, catálogo completo (con el resto de filtros aplicados)."""
    assert _nombres(client, categoria_id=99) == _nombres(client)
    assert _nombres(client, categoria_id=99, precio_max="30") == ["Pulsera de cuarzo", "Spray áurico"]


def test_combinable_con_categoria_busqueda_y_disponibles(client, tienda):
    assert _nombres(client, categoria_id=4, precio_max="42") == ["Anillo con piedra"]
    assert _nombres(client, q="cuarzo", precio_max="42") == ["Pulsera de cuarzo"]
    assert _nombres(client, precio_min="50") == ["Collar de jade"]
    assert _nombres(client, precio_min="50", solo_disponibles=True) == []


def test_con_solo_disponibles_la_variante_en_rango_debe_tener_stock(client, auth, tienda):
    """Decisión: la piedra que cumple el rango debe ser la que se puede comprar (si no, la tarjeta mostraría
    un precio fuera del rango). Amatista (40) se agota: con máximo 42 y solo disponibles, el anillo sale."""
    dar_stock(client, auth, tienda["amatista"], -2, "Se agotó")
    assert "Anillo con piedra" in _nombres(client, precio_max="42")
    assert "Anillo con piedra" not in _nombres(client, precio_max="42", solo_disponibles=True)


def test_combinable_con_intencion_en_la_misma_piedra(client, auth, engine, tienda):
    """La intención y el precio se cumplen en la MISMA piedra: Protección solo la tiene la Turmalina (45)."""
    ids = crear_intenciones(engine, ["Protección"])
    client.put(f"/admin/variantes/{tienda['turmalina']}/intenciones",
               json={"intencion_ids": [ids["Protección"]]}, headers=auth)
    assert _nombres(client, intencion_id=ids["Protección"], precio_max="50") == ["Anillo con piedra"]
    assert _nombres(client, intencion_id=ids["Protección"], precio_max="42") == []


def test_combinable_con_paginacion(client, tienda):
    pagina = client.get(URL, params={"precio_max": "45", "limite": 2}).json()
    assert len(pagina) == 2
    resto = client.get(URL, params={"precio_max": "45", "limite": 2, "desde": 2}).json()
    assert len(resto) == 1
