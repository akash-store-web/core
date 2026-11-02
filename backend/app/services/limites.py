"""T-07: límites de intentos por correo (HU023 E8 bloqueo de login, HU024 E8 solicitudes repetidas).

Viven EN MEMORIA del proceso (dict + lock): son simples y suficientes para un solo servidor.
Limitaciones conocidas: se reinician si Render reinicia o redespliega el servicio, y no se comparten
entre varias instancias (hoy hay una sola). Si algún día hay más de una, mover esto a la base o a Redis.
"""
import math
import threading
import time
from collections import defaultdict


def _ahora() -> float:
    return time.time()  # función aparte para que las pruebas puedan adelantar el reloj


class BloqueoDeLogin:
    """HU023 E8: tras `max_fallos` intentos fallidos en `ventana` segundos, el correo queda
    bloqueado `ventana` segundos. Un login correcto limpia el contador."""

    def __init__(self, max_fallos: int = 5, ventana: int = 15 * 60):
        self.max_fallos = max_fallos
        self.ventana = ventana
        self._fallos: dict[str, list[float]] = defaultdict(list)
        self._bloqueado_hasta: dict[str, float] = {}
        self._lock = threading.Lock()

    def minutos_restantes(self, email: str) -> int:
        """0 si puede intentar; si no, los minutos (redondeados hacia arriba) que faltan."""
        with self._lock:
            hasta = self._bloqueado_hasta.get(email)
            if hasta is None:
                return 0
            restante = hasta - _ahora()
            if restante <= 0:
                del self._bloqueado_hasta[email]
                self._fallos.pop(email, None)
                return 0
            return max(1, math.ceil(restante / 60))

    def registrar_fallo(self, email: str) -> None:
        with self._lock:
            ahora = _ahora()
            fallos = [t for t in self._fallos[email] if ahora - t < self.ventana]
            fallos.append(ahora)
            self._fallos[email] = fallos
            if len(fallos) >= self.max_fallos:
                self._bloqueado_hasta[email] = ahora + self.ventana

    def limpiar(self, email: str) -> None:
        with self._lock:
            self._fallos.pop(email, None)
            self._bloqueado_hasta.pop(email, None)

    def reiniciar(self) -> None:
        with self._lock:
            self._fallos.clear()
            self._bloqueado_hasta.clear()


class LimiteDeSolicitudes:
    """HU024 E8: como máximo `maximo` solicitudes por correo en `ventana` segundos (ventana deslizante)."""

    def __init__(self, maximo: int = 3, ventana: int = 60 * 60):
        self.maximo = maximo
        self.ventana = ventana
        self._solicitudes: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def permitir(self, email: str) -> bool:
        """Registra la solicitud si cabe en el límite; False si ya se alcanzó."""
        with self._lock:
            ahora = _ahora()
            recientes = [t for t in self._solicitudes[email] if ahora - t < self.ventana]
            permitido = len(recientes) < self.maximo
            if permitido:
                recientes.append(ahora)
            self._solicitudes[email] = recientes
            return permitido

    def reiniciar(self) -> None:
        with self._lock:
            self._solicitudes.clear()


bloqueo_login = BloqueoDeLogin()
limite_recuperar = LimiteDeSolicitudes()
