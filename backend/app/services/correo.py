"""Envío de correos con Brevo (API HTTP: Render gratuito bloquea los puertos SMTP).

Sin BREVO_API_KEY (desarrollo local o pruebas) el enlace se escribe en el log del servidor.
Con la llave configurada, el enlace NO se escribe en el log: abriría la cuenta a quien lea los logs.
"""
import html
import logging

import httpx

from app import config
from app.services.auth import RESTABLECER_EXPIRE_MINUTES

log = logging.getLogger("akash.correo")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _contenido_recuperacion(enlace: str) -> tuple[str, str, str]:
    asunto = "Restablece tu contraseña de Akash Store"
    texto = (
        "Hola:\n\nRecibimos una solicitud para restablecer la contraseña del panel de Akash Store.\n"
        f"Abre este enlace para elegir una nueva (vence en {RESTABLECER_EXPIRE_MINUTES} minutos y sirve una sola vez):\n\n"
        f"{enlace}\n\nSi no fuiste tú, ignora este correo: tu contraseña no cambia."
    )
    seguro = html.escape(enlace, quote=True)
    cuerpo_html = f"""<div style="font-family:Arial,sans-serif;max-width:480px;color:#333">
  <h2 style="color:#6b4c9a">Akash Store</h2>
  <p>Recibimos una solicitud para restablecer la contraseña del panel.</p>
  <p><a href="{seguro}" style="display:inline-block;padding:12px 20px;background:#6b4c9a;color:#fff;
     text-decoration:none;border-radius:6px">Elegir una nueva contraseña</a></p>
  <p style="font-size:13px">El enlace vence en {RESTABLECER_EXPIRE_MINUTES} minutos y sirve una sola vez.</p>
  <p style="font-size:13px;color:#777">Si no fuiste tú, ignora este correo: tu contraseña no cambia.</p>
</div>"""
    return asunto, texto, cuerpo_html


def enviar_enlace_recuperacion(email: str, enlace: str) -> None:
    """Nunca lanza excepciones: /auth/recuperar debe responder igual aunque el envío falle."""
    if not config.BREVO_API_KEY:
        log.warning("BREVO_API_KEY no configurada. Enlace de recuperación para %s: %s", email, enlace)
        return
    asunto, texto, cuerpo_html = _contenido_recuperacion(enlace)
    try:
        respuesta = httpx.post(
            BREVO_URL,
            headers={"api-key": config.BREVO_API_KEY, "accept": "application/json"},
            json={
                "sender": {"name": config.CORREO_REMITENTE_NOMBRE, "email": config.CORREO_REMITENTE},
                "to": [{"email": email}],
                "subject": asunto,
                "textContent": texto,
                "htmlContent": cuerpo_html,
            },
            timeout=15,
        )
        respuesta.raise_for_status()
        log.info("Correo de recuperación enviado a %s", email)
    except httpx.HTTPStatusError as error:
        # El cuerpo de Brevo explica la causa (remitente sin verificar, IP no autorizada, etc.).
        log.error("Brevo rechazó el correo para %s: %s %s", email, error.response.status_code, error.response.text[:300])
    except httpx.HTTPError as error:
        log.error("No se pudo contactar a Brevo para %s: %s", email, error)
