"""HU024: recuperar el acceso."""
import logging
import re
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.services import correo
from app.services.auth import huella_password
from tests.conftest import HASH_PRUEBA, TEST_SECRET

NUEVA = "nueva-clave-segura"


@pytest.fixture
def enlaces(monkeypatch):
    """Captura los enlaces que se 'enviarían' por correo."""
    enviados = []
    monkeypatch.setattr("app.routers.auth.enviar_enlace_recuperacion", lambda email, enlace: enviados.append((email, enlace)))
    return enviados


def _token_de(enlace: str) -> str:
    return re.search(r"token=([^&]+)", enlace).group(1)


def _login(client, password):
    return client.post("/auth/login", json={"email": "duena@example.com", "password": password})


def _restablecer(client, token, nueva=NUEVA):
    return client.post("/auth/restablecer", json={"token": token, "nueva_contrasena": nueva})


# --- POST /auth/recuperar ---

def test_recuperar_envia_enlace_al_frontend(client, enlaces):
    respuesta = client.post("/auth/recuperar", json={"email": "Duena@Example.com"})
    assert respuesta.status_code == 202
    assert len(enlaces) == 1
    email, enlace = enlaces[0]
    assert email == "duena@example.com"
    assert enlace.startswith("http://localhost:5173/restablecer?token=")


def test_misma_respuesta_si_el_correo_no_existe_o_esta_inactivo(client, enlaces):
    existe = client.post("/auth/recuperar", json={"email": "duena@example.com"}).json()
    no_existe = client.post("/auth/recuperar", json={"email": "nadie@example.com"})
    inactiva = client.post("/auth/recuperar", json={"email": "inactiva@example.com"})
    assert no_existe.status_code == inactiva.status_code == 202
    assert no_existe.json() == inactiva.json() == existe
    assert len(enlaces) == 1  # solo la cuenta activa


def test_recuperar_valida_el_email(client):
    assert client.post("/auth/recuperar", json={"email": "no-es-correo"}).status_code == 422


def test_sin_proveedor_el_enlace_queda_en_el_log(client, caplog):
    with caplog.at_level(logging.WARNING, logger="akash.correo"):
        client.post("/auth/recuperar", json={"email": "duena@example.com"})
    assert "restablecer?token=" in caplog.text


def test_correo_por_defecto_no_falla():
    correo.enviar_enlace_recuperacion("duena@example.com", "http://localhost:5173/restablecer?token=x")


# --- POST /auth/restablecer ---

def test_restablecer_con_el_enlace(client, enlaces):
    client.post("/auth/recuperar", json={"email": "duena@example.com"})
    respuesta = _restablecer(client, _token_de(enlaces[0][1]))
    assert respuesta.status_code == 200
    assert _login(client, NUEVA).status_code == 200
    assert _login(client, "clave-segura").status_code == 401


def test_el_enlace_es_de_un_solo_uso(client, enlaces):
    client.post("/auth/recuperar", json={"email": "duena@example.com"})
    token = _token_de(enlaces[0][1])
    assert _restablecer(client, token).status_code == 200
    assert _restablecer(client, token, "otra-clave-segura").status_code == 400


def test_enlace_vencido_o_manipulado(client):
    base = {"sub": "1", "tipo": "restablecer", "huella": huella_password(HASH_PRUEBA)}
    vencido = jwt.encode({**base, "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, TEST_SECRET, algorithm="HS256")
    otro_secreto = jwt.encode({**base, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                              "otro-secreto-que-no-es-el-del-servidor-32b", algorithm="HS256")
    assert _restablecer(client, vencido).status_code == 400
    assert _restablecer(client, otro_secreto).status_code == 400
    assert _restablecer(client, "basura").status_code == 400


def test_un_token_de_sesion_no_sirve_para_restablecer(client, auth):
    token_sesion = auth["Authorization"].split()[1]
    assert _restablecer(client, token_sesion).status_code == 400


def test_un_enlace_de_restablecimiento_no_abre_el_panel(client, enlaces):
    client.post("/auth/recuperar", json={"email": "duena@example.com"})
    token = _token_de(enlaces[0][1])
    assert client.get("/admin/productos", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_politica_de_contrasena(client, enlaces):
    client.post("/auth/recuperar", json={"email": "duena@example.com"})
    token = _token_de(enlaces[0][1])
    assert _restablecer(client, token, "corta").status_code == 422
    assert _restablecer(client, token, "ñ" * 40).status_code == 422  # 80 bytes > límite de bcrypt


# --- PUT /auth/contrasena ---

def test_cambiar_contrasena_con_sesion(client, auth):
    datos = {"actual": "clave-segura", "nueva": NUEVA}
    assert client.put("/auth/contrasena", json=datos, headers=auth).status_code == 200
    assert _login(client, NUEVA).status_code == 200


def test_cambiar_contrasena_validaciones(client, auth):
    assert client.put("/auth/contrasena", json={"actual": "clave-segura", "nueva": NUEVA}).status_code == 401
    assert client.put("/auth/contrasena", json={"actual": "mala", "nueva": NUEVA}, headers=auth).status_code == 400
    assert client.put("/auth/contrasena", json={"actual": "clave-segura", "nueva": "clave-segura"},
                      headers=auth).status_code == 400
    assert client.put("/auth/contrasena", json={"actual": "clave-segura", "nueva": "corta"}, headers=auth).status_code == 422


def test_cambiar_contrasena_invalida_enlaces_pendientes(client, auth, enlaces):
    client.post("/auth/recuperar", json={"email": "duena@example.com"})
    client.put("/auth/contrasena", json={"actual": "clave-segura", "nueva": NUEVA}, headers=auth)
    assert _restablecer(client, _token_de(enlaces[0][1]), "otra-clave-segura").status_code == 400


# --- Corrección en el login (HU023) ---

def test_login_con_contrasena_mayor_a_72_bytes_responde_401(client):
    assert _login(client, "x" * 100).status_code == 401
