from io import BytesIO

from PIL import Image

from app.services.optimizar_imagen import LADO_MAX, optimizar


def _foto_grande() -> bytes:
    imagen = Image.effect_noise((2400, 1600), 80).convert("RGB")
    salida = BytesIO()
    imagen.save(salida, "JPEG", quality=95)
    return salida.getvalue()


def test_reduce_tamano_y_convierte_a_webp():
    original = _foto_grande()
    nueva, tipo = optimizar(original, "image/jpeg")
    assert tipo == "image/webp"
    assert len(nueva) < len(original)
    with Image.open(BytesIO(nueva)) as resultado:
        assert max(resultado.size) <= LADO_MAX


def test_si_no_es_imagen_devuelve_el_original():
    basura = b"esto no es una foto"
    assert optimizar(basura, "image/png") == (basura, "image/png")