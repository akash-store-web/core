import os

# Antes de importar la app: las pruebas nunca tocan Supabase.
os.environ["DATABASE_URL"] = "sqlite://"
TEST_SECRET = "test-secret-only-at-least-32-bytes-long"
os.environ["JWT_SECRET"] = TEST_SECRET
# Aunque el .env local tenga la llave de Brevo, las pruebas nunca envían correos reales.
os.environ["BREVO_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  registra todas las tablas en Base.metadata
from app.database import Base, get_db
from app.main import app
from app.models.categoria import Categoria
from app.models.usuario import Usuario
from app.services.auth import hash_password

# Las 7 categorías del informe de base de datos v1.1 (sección 9).
CATEGORIAS = [
    "Boxes y kits",
    "Pulseras",
    "Collares y colgantes",
    "Anillos",
    "Roll-on",
    "Inciensos y limpieza energética",
    "Decoración y amuletos",
]

# bcrypt es lento a propósito: se cifra una sola vez para toda la suite.
HASH_PRUEBA = hash_password("clave-segura")


@pytest.fixture
def engine():
    # SQLite en memoria, solo para pruebas: create_all aquí no toca la base compartida.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _activar_fk(conexion, _):
        conexion.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Usuario(email="duena@example.com", password_hash=HASH_PRUEBA))
        db.add(Usuario(email="inactiva@example.com", password_hash=HASH_PRUEBA, activo=False))
        db.add_all(Categoria(nombre=nombre, orden=i) for i, nombre in enumerate(CATEGORIAS, start=1))
        db.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    def test_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    respuesta = client.post("/auth/login", json={"email": "duena@example.com", "password": "clave-segura"})
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}
