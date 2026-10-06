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
