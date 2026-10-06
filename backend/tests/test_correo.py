"""HU024 (AKASH-65): envío del enlace de recuperación con Brevo (simulado)."""
import logging

import httpx
import pytest

from app import config
from app.services import correo

ENLACE = "http://localhost:5173/restablecer?token=abc.def.ghi"


def test_las_pruebas_no_usan_la_llave_real():
    assert config.BREVO_API_KEY == ""


@pytest.fixture
def brevo(monkeypatch):
    """Configura Brevo con valores de prueba y captura la petición en lugar de enviarla."""
    monkeypatch.setattr(config, "BREVO_API_KEY", "llave-de-prueba")
    monkeypatch.setattr(config, "CORREO_REMITENTE", "tienda@ejemplo.com")
    monkeypatch.setattr(config, "CORREO_REMITENTE_NOMBRE", "Akash Store")
    enviadas = []

    def post(url, headers, json, timeout):
        enviadas.append({"url": url, "headers": headers, "json": json})
        return httpx.Response(201, json={"messageId": "<1@brevo>"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(correo.httpx, "post", post)
    return enviadas


def test_envia_con_brevo(brevo):
    correo.enviar_enlace_recuperacion("duena@example.com", ENLACE)
    assert len(brevo) == 1
    peticion = brevo[0]
    assert peticion["url"] == "https://api.brevo.com/v3/smtp/email"
    assert peticion["headers"]["api-key"] == "llave-de-prueba"
    cuerpo = peticion["json"]
    assert cuerpo["sender"] == {"name": "Akash Store", "email": "tienda@ejemplo.com"}
    assert cuerpo["to"] == [{"email": "duena@example.com"}]
    assert "Restablece tu contraseña" in cuerpo["subject"]
    assert ENLACE in cuerpo["textContent"]
    assert "30 minutos" in cuerpo["textContent"]
    assert 'href="http://localhost:5173/restablecer?token=abc.def.ghi"' in cuerpo["htmlContent"]


def test_con_brevo_el_enlace_no_va_al_log(brevo, caplog):
    with caplog.at_level(logging.INFO, logger="akash.correo"):
        correo.enviar_enlace_recuperacion("duena@example.com", ENLACE)
    assert "token=" not in caplog.text


def test_si_brevo_rechaza_se_registra_y_no_falla(monkeypatch, brevo, caplog):
    def rechazo(url, headers, json, timeout):
        return httpx.Response(401, json={"message": "Key not found"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(correo.httpx, "post", rechazo)
    with caplog.at_level(logging.ERROR, logger="akash.correo"):
        correo.enviar_enlace_recuperacion("duena@example.com", ENLACE)  # no lanza
    assert "401" in caplog.text and "Key not found" in caplog.text
    assert "token=" not in caplog.text


def test_si_brevo_no_responde_no_falla(monkeypatch, brevo, caplog):
    def caido(url, headers, json, timeout):
        raise httpx.ConnectTimeout("sin respuesta")

    monkeypatch.setattr(correo.httpx, "post", caido)
    with caplog.at_level(logging.ERROR, logger="akash.correo"):
        correo.enviar_enlace_recuperacion("duena@example.com", ENLACE)
    assert "No se pudo contactar a Brevo" in caplog.text


def test_sin_llave_el_enlace_va_al_log(caplog):
    with caplog.at_level(logging.WARNING, logger="akash.correo"):
        correo.enviar_enlace_recuperacion("duena@example.com", ENLACE)
    assert ENLACE in caplog.text


def test_el_enlace_se_escapa_en_el_html():
    _, _, cuerpo_html = correo._contenido_recuperacion('http://x/?a=1&b="<script>"')
    assert "<script>" not in cuerpo_html
    assert "&amp;b=" in cuerpo_html


def test_recuperar_envia_en_segundo_plano_con_brevo(client, brevo):
    respuesta = client.post("/auth/recuperar", json={"email": "duena@example.com"})
    assert respuesta.status_code == 202
    assert [p["json"]["to"] for p in brevo] == [[{"email": "duena@example.com"}]]
    assert "/restablecer?token=" in brevo[0]["json"]["textContent"]


def test_recuperar_con_correo_inexistente_no_llama_a_brevo(client, brevo):
    assert client.post("/auth/recuperar", json={"email": "nadie@example.com"}).status_code == 202
    assert brevo == []
