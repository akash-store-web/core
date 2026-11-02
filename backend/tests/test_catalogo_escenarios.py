"""Escenarios del catálogo público que faltaban: HU001 (paginación, datos incompletos, parámetros manipulados),
HU002 (precio "desde" con disponibles), HU003 (reservas, última unidad, existencias negativas) y HU029 (agotados al final)."""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.variante import Variante
from app.services import carrito
from tests.fabricas import dar_stock

SPRAY = {
    "categoria_id": 6,
    "nombre": "Spray áurico",
    "descripcion": "Spray de 60 ml con agua floral y aceites esenciales.",
    "precio_base": "25.00",
}
ANILLO = {
    "categoria_id": 4,
    "nombre": "Anillo de plata 925 con piedra",
    "descripcion": "Anillo de plata 925 con piedra natural facetada.",
    "precio_base": "40.00",
    "es_pieza_natural": True,
}


def _crear(client, auth, datos, stock=2, publicar=True):
    pid = client.post("/admin/productos", json=datos, headers=auth).json()["id"]
    if stock:
        dar_stock(client, auth, _unica(client, auth, pid), stock)
    if publicar:
        assert client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth).status_code == 200
    return pid


def _unica(client, auth, pid):
    return client.get(f"/admin/productos/{pid}/variantes", headers=auth).json()[0]["id"]


def _agotar(client, auth, variante_id, cantidad):
    dar_stock(client, auth, variante_id, -cantidad, "Se agotó")


def _nombres(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return [p["nombre"] for p in respuesta.json()]


# ---------- HU029 Esc.2: agotados al final ----------

def test_agotados_al_final_aunque_el_orden_alfabetico_diga_otra_cosa(client, auth):
    """Alfabéticamente «Aguas…» va antes que «Velas…», pero está agotado: debe ir al final.
    Entre categorías: Anillos (orden menor) agotado queda después de Inciensos disponible."""
    aguas = _crear(client, auth, {**SPRAY, "nombre": "Aguas florales"})
    _crear(client, auth, {**SPRAY, "nombre": "Velas de soya"})
    anillo = _crear(client, auth, ANILLO)
    _agotar(client, auth, _unica(client, auth, aguas), 2)
    _agotar(client, auth, _unica(client, auth, anillo), 2)

    assert _nombres(client.get("/catalogo")) == [
        "Velas de soya",  # disponible
        "Anillo de plata 925 con piedra",  # agotado, categoría Anillos (va antes que Inciensos)
        "Aguas florales",  # agotado, categoría Inciensos
    ]
    assert _nombres(client.get("/catalogo", params={"solo_disponibles": True})) == ["Velas de soya"]


# ---------- HU001: paginación y parámetros manipulados ----------

def test_paginacion_con_limite_y_desde(client, auth):
    for nombre in ["Spray A", "Spray B", "Spray C"]:
        _crear(client, auth, {**SPRAY, "nombre": nombre})
    assert _nombres(client.get("/catalogo", params={"limite": 2})) == ["Spray A", "Spray B"]
    assert _nombres(client.get("/catalogo", params={"limite": 2, "desde": 2})) == ["Spray C"]
    assert client.get("/catalogo", params={"desde": 50}).json() == []  # página vacía, no error
    assert len(client.get("/catalogo", params={"limite": 100}).json()) == 3


def test_paginacion_fuera_de_rango_es_422(client):
    for params in ({"limite": 0}, {"limite": 101}, {"limite": -1}, {"desde": -1}, {"limite": "diez"}):
        assert client.get("/catalogo", params=params).status_code == 422, params


def test_parametros_desconocidos_se_ignoran_y_no_muestran_despublicados(client, auth):
    _crear(client, auth, SPRAY)
    _crear(client, auth, {**SPRAY, "nombre": "Spray en borrador"}, publicar=False)
    respuesta = client.get("/catalogo", params={"publicado": "false", "incluir_ocultos": 1, "orden": "costo"})
    assert _nombres(respuesta) == ["Spray áurico"]


# ---------- HU001 E7 / HU002 E8: datos incompletos ----------

def test_producto_publicado_con_precio_cero_no_se_lista(client, auth, engine, caplog):
    _crear(client, auth, SPRAY)
    malo = _crear(client, auth, {**SPRAY, "nombre": "Spray sin precio"})
    with Session(engine) as db:  # datos dañados por fuera de la API (la API exige precio > 0)
        db.get(Producto, malo).precio_base = Decimal("0")
        db.commit()

    with caplog.at_level(logging.WARNING, logger="akash.catalogo"):
        assert _nombres(client.get("/catalogo")) == ["Spray áurico"]
        assert client.get(f"/catalogo/{malo}").status_code == 404
    assert any(str(malo) in r.getMessage() for r in caplog.records)


def test_variante_con_precio_negativo_oculta_el_producto(client, auth, engine):
    pid = _crear(client, auth, SPRAY)
    with Session(engine) as db:
        db.get(Variante, _unica(client, auth, pid)).precio = Decimal("-5.00")
        db.commit()
    assert client.get("/catalogo").json() == []
    assert client.get(f"/catalogo/{pid}").status_code == 404


def test_producto_publicado_sin_variantes_no_se_lista(client, auth, engine, caplog):
    pid = _crear(client, auth, SPRAY, stock=0)
    with Session(engine) as db:
        db.delete(db.get(Variante, _unica(client, auth, pid)))
        db.commit()
    with caplog.at_level(logging.WARNING, logger="akash.catalogo"):
        assert client.get("/catalogo").json() == []
        assert client.get(f"/catalogo/{pid}").status_code == 404
    assert any(str(pid) in r.getMessage() for r in caplog.records)


# ---------- HU002 E7: precio "desde" solo con disponibles ----------

def _anillo_con_dos_precios(client, auth):
    """Amatista S/ 45 (3 u.) y Turmalina S/ 40 (2 u.)."""
    pid = _crear(client, auth, ANILLO, stock=3, publicar=False)
    amatista = _unica(client, auth, pid)
    client.put(f"/admin/productos/{pid}/variantes/{amatista}", json={"nombre": "Amatista", "precio": "45.00"},
               headers=auth)
    turmalina = client.post(f"/admin/productos/{pid}/variantes", json={"nombre": "Turmalina negra"}, headers=auth).json()
    dar_stock(client, auth, turmalina["id"], 2)
    client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth)
    return pid, amatista, turmalina["id"]


def test_precio_desde_ignora_las_variantes_agotadas(client, auth):
    pid, _, turmalina = _anillo_con_dos_precios(client, auth)
    _agotar(client, auth, turmalina, 2)  # la de S/ 40 se agota: ya no se puede comprar a ese precio
    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["precio"], tarjeta["precio_desde"], tarjeta["disponible"]) == ("45.00", False, True)
    assert client.get(f"/catalogo/{pid}").json()["precio"] == "45.00"


def test_precio_desde_con_todas_agotadas_usa_todas(client, auth):
    _, amatista, turmalina = _anillo_con_dos_precios(client, auth)
    _agotar(client, auth, amatista, 3)
    _agotar(client, auth, turmalina, 2)
    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["precio"], tarjeta["precio_desde"], tarjeta["disponible"]) == ("40.00", True, False)


# ---------- HU003: reservas, última unidad, existencias negativas ----------

def test_ultima_unidad_en_la_ficha(client, auth):
    pid, amatista, turmalina = _anillo_con_dos_precios(client, auth)
    _agotar(client, auth, amatista, 2)  # queda 1
    variantes = {v["id"]: v for v in client.get(f"/catalogo/{pid}").json()["variantes"]}
    assert (variantes[amatista]["disponible"], variantes[amatista]["ultima_unidad"]) == (True, True)
    assert (variantes[turmalina]["disponible"], variantes[turmalina]["ultima_unidad"]) == (True, False)

    _agotar(client, auth, amatista, 1)  # agotada: ya no es "última unidad"
    variantes = {v["id"]: v for v in client.get(f"/catalogo/{pid}").json()["variantes"]}
    assert (variantes[amatista]["disponible"], variantes[amatista]["ultima_unidad"]) == (False, False)


def test_reservas_descuentan_la_disponibilidad(client, auth, monkeypatch):
    """HU003 E5: las unidades apartadas por pedidos vigentes no están disponibles para otra clienta."""
    pid, amatista, turmalina = _anillo_con_dos_precios(client, auth)  # 3 y 2 unidades
    monkeypatch.setattr(carrito, "unidades_reservadas", lambda db, ids: {amatista: 2, turmalina: 2})

    variantes = {v["id"]: v for v in client.get(f"/catalogo/{pid}").json()["variantes"]}
    assert (variantes[amatista]["disponible"], variantes[amatista]["ultima_unidad"]) == (True, True)  # 3 - 2 = 1
    assert variantes[turmalina]["disponible"] is False  # 2 - 2 = 0
    tarjeta = client.get("/catalogo").json()[0]
    assert (tarjeta["precio"], tarjeta["precio_desde"]) == ("45.00", False)

    monkeypatch.setattr(carrito, "unidades_reservadas", lambda db, ids: {amatista: 3, turmalina: 2})
    assert client.get("/catalogo").json()[0]["disponible"] is False
    assert client.get("/catalogo", params={"solo_disponibles": True}).json() == []


def test_existencias_negativas_se_muestran_como_agotado(client, auth, engine):
    pid = _crear(client, auth, SPRAY)
    variante = _unica(client, auth, pid)
    with Session(engine) as db:  # dato inconsistente por fuera de registrar_movimiento
        db.get(Variante, variante).existencias = -3
        db.commit()
    assert client.get("/catalogo").json()[0]["disponible"] is False
    ficha_variante = client.get(f"/catalogo/{pid}").json()["variantes"][0]
    assert (ficha_variante["disponible"], ficha_variante["ultima_unidad"]) == (False, False)


# ---------- Datos internos: nunca en las respuestas públicas ----------

PROHIBIDAS = {"existencias", "existencias_total", "costo", "costo_unitario", "proveedor", "ruc", "publicado",
              "saldo", "movimientos", "compras", "creado_en", "actualizado_en"}


def _claves(objeto):
    if isinstance(objeto, dict):
        return set(objeto) | {c for v in objeto.values() for c in _claves(v)}
    if isinstance(objeto, list):
        return {c for v in objeto for c in _claves(v)}
    return set()


def test_tarjeta_y_ficha_no_exponen_costos_proveedores_ni_existencias(client, auth):
    pid, _, _ = _anillo_con_dos_precios(client, auth)
    tarjetas = client.get("/catalogo").json()
    ficha = client.get(f"/catalogo/{pid}").json()
    assert not _claves(tarjetas) & PROHIBIDAS
    assert not _claves(ficha) & PROHIBIDAS
    assert set(ficha["variantes"][0]) == {"id", "nombre", "precio", "disponible", "ultima_unidad", "propiedades"}
    # Las cantidades exactas (3 y 2) no aparecen como valores numéricos en la ficha
    assert all(not isinstance(v, int) or k == "id" for var in ficha["variantes"] for k, v in var.items()
               if not isinstance(v, bool))


# ---------- HU028 E8: variantes desactivadas ----------

def test_variante_desactivada_no_aparece_ni_cuenta_en_el_catalogo(client, auth):
    """Una variante con historial se desactiva al eliminarla: la clienta no la ve en la ficha,
    no cuenta para la disponibilidad ni para el precio «desde»."""
    pid = _crear(client, auth, ANILLO, stock=0, publicar=False)
    base = f"/admin/productos/{pid}/variantes"
    jade = client.post(base, json={"nombre": "Jade", "precio": "90.00"}, headers=auth).json()["id"]
    dar_stock(client, auth, _unica(client, auth, pid), 1)
    dar_stock(client, auth, jade, 3)
    assert client.patch(f"/admin/productos/{pid}/publicado", json={"publicado": True}, headers=auth).status_code == 200

    r = client.delete(f"{base}/{jade}", headers=auth)
    assert r.status_code == 200 and r.json()["desactivada"] is True

    ficha = client.get(f"/catalogo/{pid}").json()
    assert [v["id"] for v in ficha["variantes"]] == [_unica(client, auth, pid)]
    assert ficha["precio"] == "40.00" and ficha["precio_desde"] is False
    tarjeta = next(p for p in client.get("/catalogo").json() if p["id"] == pid)
    assert tarjeta["precio_desde"] is False and tarjeta["disponible"] is True
