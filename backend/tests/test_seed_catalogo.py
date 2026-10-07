"""T-01 #3: el seed del catálogo real pasa por las mismas validaciones que la API."""
import pytest
from sqlalchemy.orm import Session

from app import config
from app.models.imagen import Imagen
from app.models.producto import Producto
from app.models.variante import Variante
from app.services import storage
from scripts.catalogo_datos import leer_catalogo
from scripts.seed_catalogo import cargar

CATALOGO = leer_catalogo()
CON_PRECIO = [p for p in CATALOGO if p["precio_base"] is not None]
JPG = b"\xff\xd8\xff\xe0" + b"0" * 100


def _filas(client, auth):
    return {f["nombre"]: f for f in client.get("/admin/productos", headers=auth).json()}


def test_simulacion_no_escribe(engine):
    with Session(engine) as db:
        cargar(db, aplicar=False)
        assert db.query(Producto).count() == 0


def test_carga_el_catalogo_real_despublicado(engine, client, auth):
    with Session(engine) as db:
        cargar(db, aplicar=True)
        assert db.query(Producto).count() == len(CON_PRECIO)
        assert db.query(Producto).filter(Producto.publicado.is_(True)).count() == 0
    filas = _filas(client, auth)
    assert filas["Pulsera de cuarzo"]["num_variantes"] == 12
    assert filas["Spray áurico"]["num_variantes"] == 1  # variante "Única"
    assert "Pack citrino" not in filas  # sin precio en la hoja: pendiente de confirmar


def test_las_existencias_arrancan_en_cero_o_en_lo_pedido(engine):
    with Session(engine) as db:
        cargar(db, aplicar=True)
        assert db.query(Variante).filter(Variante.existencias != 0).count() == 0
    with Session(engine) as db:
        db.query(Variante).delete()
        db.query(Producto).delete()
        db.commit()
        cargar(db, aplicar=True, existencias=2)
        assert db.query(Variante).filter(Variante.existencias != 2).count() == 0


def test_pulsera_de_cuarzo_con_sus_12_piedras(engine, client, auth):
    with Session(engine) as db:
        cargar(db, aplicar=True)
    pulsera = _filas(client, auth)["Pulsera de cuarzo"]["id"]
    variantes = client.get(f"/admin/productos/{pulsera}/variantes", headers=auth).json()
    assert len(variantes) == 12
    assert {v["precio_efectivo"] for v in variantes} == {"45.00"}  # todas heredan el precio base
    assert all(v["propiedades"] for v in variantes)


def test_collar_de_amatista_con_doble_precio(engine, client, auth, monkeypatch):
    monkeypatch.setattr(config, "PUBLICAR_EXIGE_FOTO", False)  # aunque el .env local lo active
    with Session(engine) as db:
        cargar(db, aplicar=True)
    collar = _filas(client, auth)["Collar de amatista"]["id"]
    precios = {v["nombre"]: v["precio_efectivo"]
               for v in client.get(f"/admin/productos/{collar}/variantes", headers=auth).json()}
    assert precios == {"Dorado (media luna)": "55.00", "Plateado (druza)": "60.00"}
    client.patch(f"/admin/productos/{collar}/publicado", json={"publicado": True}, headers=auth)
    tarjeta = next(p for p in client.get("/catalogo").json() if p["id"] == collar)
    assert (tarjeta["precio"], tarjeta["precio_desde"]) == ("55.00", True)  # "Desde S/ 55.00"


def test_es_idempotente(engine):
    with Session(engine) as db:
        cargar(db, aplicar=True)
        variantes = db.query(Variante).count()
        cargar(db, aplicar=True)
        assert db.query(Producto).count() == len(CON_PRECIO)
        assert db.query(Variante).count() == variantes


@pytest.fixture
def bucket(monkeypatch):
    """Storage en memoria: {ruta: bytes}."""
    archivos = {}
    monkeypatch.setattr(config, "SUPABASE_URL", "https://prueba.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_BUCKET", "productos")

    def subir(ruta, contenido, content_type):
        archivos[ruta] = contenido
        return storage.url_publica(ruta)

    monkeypatch.setattr(storage, "subir", subir)
    return archivos


def test_sube_las_fotos_de_la_carpeta_del_producto(engine, bucket, tmp_path):
    carpeta = tmp_path / "collar-de-amatista"
    carpeta.mkdir()
    (carpeta / "1.jpg").write_bytes(JPG)
    (carpeta / "2.jpg").write_bytes(JPG)
    (carpeta / "notas.txt").write_text("no es una foto")
    with Session(engine) as db:
        cargar(db, aplicar=True, carpeta_fotos=tmp_path)
        collar = db.query(Producto).filter_by(nombre="Collar de amatista").one()
        assert [i.es_principal for i in collar.imagenes] == [True, False]
        assert db.query(Imagen).count() == 2
    assert len(bucket) == 2


def test_fotos_en_simulacion_no_suben_nada(engine, bucket, tmp_path):
    carpeta = tmp_path / "collar-de-amatista"
    carpeta.mkdir()
    (carpeta / "1.jpg").write_bytes(JPG)
    with Session(engine) as db:
        cargar(db, aplicar=False, carpeta_fotos=tmp_path)
        assert db.query(Imagen).count() == 0
    assert bucket == {}
