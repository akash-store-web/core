from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends

from app.deps import get_current_user
from app.main import app
from app.models.usuario import Usuario
from tests.conftest import TEST_SECRET


@app.get("/__test_protected")
def protected(user: Usuario = Depends(get_current_user)):
    return {"id": user.id}


def _login(client, email="duena@example.com", password="clave-segura"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _token(sub="1", exp_delta=timedelta(minutes=5), secret=TEST_SECRET):
    return jwt.encode({"sub": sub, "exp": datetime.now(timezone.utc) + exp_delta}, secret, algorithm="HS256")


def test_login_valid_credentials_and_protected_dependency(client):
    response = _login(client)
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"
    protected_response = client.get("/__test_protected", headers={"Authorization": f"Bearer {token}"})
    assert protected_response.status_code == 200
    assert protected_response.json() == {"id": 1}


def test_login_email_is_case_insensitive(client):
    assert _login(client, email="Duena@Example.com").status_code == 200


def test_login_invalid_credentials(client):
    assert _login(client, password="incorrecta").status_code == 401


def test_login_unknown_email(client):
    assert _login(client, email="nadie@example.com").status_code == 401


def test_login_inactive_user(client):
    assert _login(client, email="inactiva@example.com").status_code == 401


def test_expired_token(client):
    token = _token(exp_delta=timedelta(seconds=-1))
    response = client.get("/__test_protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expirado"


def test_missing_token(client):
    assert client.get("/__test_protected").status_code == 401


def test_token_signed_with_other_secret(client):
    token = _token(secret="otro-secreto-que-no-es-el-del-servidor-32b")
    response = client.get("/__test_protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_token_of_inactive_user(client):
    response = client.get("/__test_protected", headers={"Authorization": f"Bearer {_token(sub='2')}"})
    assert response.status_code == 401


# --- T-07 (HU023 E5 a E9): escenarios de error ---

def test_campos_vacios_o_correo_mal_escrito_responden_422_sin_consultar_la_base(client, monkeypatch):
    def no_debe_consultar(*args, **kwargs):
        raise AssertionError("no debía consultar la base")

    monkeypatch.setattr("app.routers.auth.verify_password", no_debe_consultar)
    assert _login(client, password="").status_code == 422
    assert _login(client, email="").status_code == 422
    assert _login(client, email="duena-sin-arroba").status_code == 422
    assert client.post("/auth/login", json={}).status_code == 422


def test_bloqueo_tras_cinco_intentos_fallidos(client, monkeypatch):
    from app.services import limites
    reloj = [1_000_000.0]
    monkeypatch.setattr(limites, "_ahora", lambda: reloj[0])
    for _ in range(5):
        assert _login(client, password="incorrecta").status_code == 401
    bloqueado = _login(client)  # ni siquiera con la contraseña correcta
    assert bloqueado.status_code == 429
    assert bloqueado.json()["detail"].startswith("Demasiados intentos fallidos; vuelve a intentarlo en 15 minutos")
    assert bloqueado.headers["Retry-After"] == "900"
    assert _login(client, email="DUENA@example.com").status_code == 429  # mismo correo en otra capitalización
    assert _login(client, email="otra@example.com", password="x").status_code == 401  # otros correos no se bloquean
    reloj[0] += 14 * 60 + 30
    assert "1 minuto" in _login(client).json()["detail"]
    reloj[0] += 31
    assert _login(client).status_code == 200


def test_login_correcto_reinicia_el_contador(client, monkeypatch):
    from app.services import limites
    reloj = [1_000_000.0]
    monkeypatch.setattr(limites, "_ahora", lambda: reloj[0])
    for _ in range(4):
        _login(client, password="incorrecta")
    assert _login(client).status_code == 200
    for _ in range(4):
        assert _login(client, password="incorrecta").status_code == 401
    assert _login(client).status_code == 200


def test_fallos_fuera_de_la_ventana_no_suman(client, monkeypatch):
    from app.services import limites
    reloj = [1_000_000.0]
    monkeypatch.setattr(limites, "_ahora", lambda: reloj[0])
    for _ in range(4):
        _login(client, password="incorrecta")
    reloj[0] += 15 * 60 + 1
    assert _login(client, password="incorrecta").status_code == 401
    assert _login(client).status_code == 200


def test_token_alterado(client):
    token = _login(client).json()["access_token"]
    cabecera, cuerpo, firma = token.split(".")
    alterado = f"{cabecera}.{cuerpo[:-2]}xx.{firma}"
    response = client.get("/__test_protected", headers={"Authorization": f"Bearer {alterado}"})
    assert response.status_code == 401
    assert client.get("/__test_protected", headers={"Authorization": "Bearer no-es-un-jwt"}).status_code == 401
