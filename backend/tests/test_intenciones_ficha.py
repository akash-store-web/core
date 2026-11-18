"""HU005 (AKASH-168): intenciones de cada piedra en la ficha pública. Datos ficticios.
Reutiliza las fixtures de HU008 (tests/test_intenciones.py)."""
from sqlalchemy import text

from tests.test_intenciones import _asignar, ids, tienda  # noqa: F401  (fixtures de pytest)


def _ficha(client, nombre):
    pid = next(p["id"] for p in client.get("/catalogo").json() if p["nombre"] == nombre)
    return client.get(f"/catalogo/{pid}").json()


def test_ficha_muestra_las_intenciones_de_cada_piedra(client, tienda):
    """HU005 Esc.1: texto plano, ordenadas por nombre."""
    variantes = {v["nombre"]: v["intenciones"] for v in _ficha(client, "Pulsera de cuarzo")["variantes"]}
    assert variantes == {"Amatista": ["Calma y paz interior", "Protección"], "Citrino": ["Abundancia y prosperidad"]}


def test_ficha_sin_intenciones_trae_lista_vacia(client, tienda):
    """HU005 E3/E4."""
    assert _ficha(client, "Spray áurico")["variantes"][0]["intenciones"] == []


def test_un_cambio_en_el_panel_se_ve_en_la_ficha(client, auth, ids, tienda):
    """HU005 Esc.2: sin pasos adicionales."""
    _asignar(client, auth, tienda["citrino"], [ids["Energía y vitalidad"], ids["Buena suerte"]])
    citrino = next(v for v in _ficha(client, "Pulsera de cuarzo")["variantes"] if v["nombre"] == "Citrino")
    assert citrino["intenciones"] == ["Buena suerte", "Energía y vitalidad"]


def test_intencion_desactivada_deja_de_salir_en_la_ficha(client, engine, ids, tienda):
    """HU005 E5: la asignación se conserva en la base, pero no se muestra."""
    with engine.begin() as conexion:
        conexion.execute(text("UPDATE intencion SET activa = 0 WHERE id = :id"), {"id": ids["Calma y paz interior"]})
    amatista = next(v for v in _ficha(client, "Pulsera de cuarzo")["variantes"] if v["nombre"] == "Amatista")
    assert amatista["intenciones"] == ["Protección"]
