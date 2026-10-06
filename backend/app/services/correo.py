"""Envío de correos. PENDIENTE (HU024): elegir proveedor con el equipo (p. ej. Resend o SMTP de Gmail)
y agregar aquí sus variables de entorno. Mientras tanto, el enlace se escribe en el log del servidor,
que solo ve el equipo en Render."""
import logging

log = logging.getLogger("akash.correo")


def enviar_enlace_recuperacion(email: str, enlace: str) -> None:
    log.warning("Sin proveedor de correo configurado. Enlace de recuperación para %s: %s", email, enlace)
