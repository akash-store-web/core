"""El script de productos de ejemplo pasa por las mismas validaciones que la API."""
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.variante import Variante
from scripts.seed_productos import PRODUCTOS, cargar


def test_simulacion_no_escribe(engine):
    with Session(engine) as db:
        cargar(db, aplicar=False)
        assert db.query(Producto).count() == 0


def test_carga_productos_despublicados_con_sus_variantes(engine, client, auth):
    with Session(engine) as db:
        cargar(db, aplicar=True)
        assert db.query(Producto).count() == len(PRODUCTOS)
        assert db.query(Producto).filter(Producto.publicado.is_(True)).count() == 0

    filas = {f["nombre"]: f for f in client.get("/admin/productos", headers=auth).json()}
    assert filas["Pulsera de cuarzo"]["num_variantes"] == 12
    assert filas["Spray áurico"]["num_variantes"] == 1  # variante "Única"
    assert all(f["foto_generica"] for f in filas.values())  # sin fotos reales: imagen genérica

    anillo = filas["Anillo de plata 925 con piedra"]["id"]
    precios = {v["nombre"]: v["precio_efectivo"]
               for v in client.get(f"/admin/productos/{anillo}/variantes", headers=auth).json()}
    assert precios == {"Amatista": "45.00", "Turmalina negra": "40.00"}


def test_es_idempotente(engine):
    with Session(engine) as db:
        cargar(db, aplicar=True)
        variantes = db.query(Variante).count()
        cargar(db, aplicar=True)
        assert db.query(Producto).count() == len(PRODUCTOS)
        assert db.query(Variante).count() == variantes
