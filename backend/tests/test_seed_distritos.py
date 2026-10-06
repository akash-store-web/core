from sqlalchemy.orm import Session

from app.models.distrito import Distrito
from scripts.seed_distritos import CALLAO, DISTRITOS, LIMA_METROPOLITANA, cargar


def test_lista_completa_y_sin_repetidos():
    assert len(LIMA_METROPOLITANA) == 43
    assert len(CALLAO) == 7
    assert len({d.lower() for d in DISTRITOS}) == len(DISTRITOS)
    assert all(len(d) <= 60 for d in DISTRITOS)  # distrito.nombre es VARCHAR(60)


def test_simulacion_no_escribe(engine):
    with Session(engine) as db:
        assert cargar(db, aplicar=False) == 50
        assert db.query(Distrito).count() == 0


def test_carga_sin_cobertura_e_idempotente(engine, client):
    with Session(engine) as db:
        db.add(Distrito(nombre="miraflores"))  # ya existente, otra capitalización
        db.commit()
        assert cargar(db, aplicar=True) == 49
        assert cargar(db, aplicar=True) == 0
        assert db.query(Distrito).count() == 50
    publicos = client.get("/envio/distritos").json()
    assert all(d["con_cobertura"] is False for d in publicos)
