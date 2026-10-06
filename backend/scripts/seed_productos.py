"""Carga productos de ejemplo de Akash Store (bisutería y joyería con piedras naturales).

- Se crean DESPUBLICADOS y sin fotos: la propietaria revisa, sube fotos y publica (HU016).
- Nombres, piedras y familias salen del Catálogo 2025 (informe de BD v1.1, sección 9). El precio
  del anillo (S/ 45 amatista, S/ 40 turmalina) es real (HU027); los demás precios y existencias son
  REFERENCIALES y deben confirmarse con la propietaria antes de publicar (T-01 #2).
- Las propiedades se redactan como creencias atribuidas, no como promesas de salud.
- Idempotente: si ya existe un producto con el mismo nombre, lo salta.

Uso (desde backend/, con DATABASE_URL en .env):
    python -m scripts.seed_productos            # simulación: no escribe nada
    python -m scripts.seed_productos --aplicar  # carga en la base
"""
import argparse
from decimal import Decimal

from app import models  # noqa: F401  registra todos los modelos para las relaciones
from app.database import SessionLocal
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.variante import Variante
from app.schemas.producto import ProductoCrear
from app.services.productos import crear_producto

PROPIEDADES = {
    "Amatista": "Se le atribuye calma, intuición y descanso.",
    "Citrino": "Asociada a la abundancia, la alegría y la creatividad.",
    "Cuarzo rosa": "Piedra del amor propio y la armonía en las relaciones.",
    "Cuarzo blanco": "Considerada amplificadora de energía y claridad mental.",
    "Cuarzo ahumado": "Se le atribuye arraigo y liberación de tensiones.",
    "Ojo de tigre": "Asociada a la protección, la confianza y la determinación.",
    "Pirita": "Piedra tradicional de la prosperidad y la buena suerte.",
    "Turmalina negra": "Considerada protectora frente a energías negativas.",
    "Jade": "Asociada al equilibrio, la serenidad y la buena fortuna.",
    "Howlita": "Se le atribuye paciencia y calma ante el estrés.",
    "Piedra luna": "Vinculada a la intuición, los ciclos y la feminidad.",
    "Lapislázuli": "Asociada a la sabiduría, la verdad y la comunicación.",
    "Labradorita": "Considerada piedra de la transformación y la protección del aura.",
    "Ágata": "Se le atribuye estabilidad y equilibrio emocional.",
}


def v(nombre, existencias, precio=None, propiedades=None):
    return {"nombre": nombre, "existencias": existencias, "precio": precio,
            "propiedades": propiedades or PROPIEDADES.get(nombre)}


PRODUCTOS = [
    {
        "categoria": "Pulseras", "nombre": "Pulsera de cuarzo",
        "descripcion": "Pulsera de cuentas de piedra natural de 8 mm con hilo elástico reforzado. "
                       "Se adapta a la mayoría de muñecas y combina con otras pulseras.",
        "precio_base": "25.00", "material": "Piedra natural e hilo elástico", "medidas": "Cuentas de 8 mm",
        "es_pieza_natural": True,
        "variantes": [v(p, 4) for p in ["Cuarzo rosa", "Ojo de tigre", "Pirita", "Turmalina negra", "Amatista",
                                        "Citrino", "Jade", "Howlita", "Piedra luna", "Lapislázuli",
                                        "Cuarzo ahumado", "Labradorita"]],
    },
    {
        "categoria": "Pulseras", "nombre": "Pulsera de los 7 chakras",
        "descripcion": "Pulsera con siete piedras naturales, una por cada chakra, separadas por cuentas "
                       "de lava volcánica donde puedes aplicar unas gotas de aceite esencial.",
        "precio_base": "28.00", "material": "Piedras naturales y lava volcánica", "medidas": "Cuentas de 8 mm",
        "es_pieza_natural": True, "existencias": 6,
    },
    {
        "categoria": "Pulseras", "nombre": "Pulsera ojo turco",
        "descripcion": "Pulsera tejida en hilo encerado con dije de ojo turco, amuleto tradicional "
                       "de protección. Cierre corredizo ajustable.",
        "precio_base": "15.00", "material": "Hilo encerado y vidrio", "medidas": "Ajustable",
        "variantes": [v("Rojo", 5, propiedades=None), v("Negro", 5), v("Celeste", 4)],
    },
    {
        "categoria": "Collares y colgantes", "nombre": "Collar de amatista",
        "descripcion": "Colgante de punta de amatista natural engarzada, con cadena de acero quirúrgico "
                       "que no se oscurece ni causa alergia.",
        "precio_base": "35.00", "material": "Amatista y acero quirúrgico", "medidas": "Punta de 3 cm; cadena de 45 cm",
        "es_pieza_natural": True, "existencias": 5,
    },
    {
        "categoria": "Collares y colgantes", "nombre": "Colgante de punta de cuarzo",
        "descripcion": "Punta de cuarzo natural envuelta en alambre, con cordón de algodón regulable. "
                       "Cada punta tiene forma y brillo únicos.",
        "precio_base": "30.00", "material": "Cuarzo natural y alambre", "medidas": "Punta de 3 a 4 cm",
        "es_pieza_natural": True,
        "variantes": [v("Cuarzo blanco", 3), v("Cuarzo rosa", 3), v("Ojo de tigre", 2),
                      v("Ágata", 2), v("Turmalina negra", 2, precio="32.00")],
    },
    {
        "categoria": "Anillos", "nombre": "Anillo de plata 925 con piedra",
        "descripcion": "Anillo de plata 925 con piedra natural facetada. Indica tu talla al comprar.",
        "precio_base": "40.00", "material": "Plata 925 y piedra natural", "medidas": "Piedra de 8 × 10 mm",
        "es_pieza_natural": True,
        "variantes": [v("Amatista", 3, precio="45.00"), v("Turmalina negra", 3)],
    },
    {
        "categoria": "Anillos", "nombre": "Anillo ojo turco",
        "descripcion": "Anillo ajustable bañado en plata con ojo turco esmaltado.",
        "precio_base": "18.00", "material": "Aleación bañada en plata", "medidas": "Ajustable",
        "existencias": 8,
    },
    {
        "categoria": "Roll-on", "nombre": "Roll-on de cuarzo",
        "descripcion": "Roll-on de 10 ml con aceite esencial y chips de piedra natural en su interior. "
                       "Aplícalo en muñecas y cuello.",
        "precio_base": "30.00", "material": "Vidrio, aceite esencial y chips de piedra", "medidas": "10 ml",
        "variantes": [v("Amatista", 4, propiedades="Aroma lavanda. " + PROPIEDADES["Amatista"]),
                      v("Citrino", 4, propiedades="Aroma naranja. " + PROPIEDADES["Citrino"]),
                      v("Jade", 3, propiedades="Aroma eucalipto. " + PROPIEDADES["Jade"]),
                      v("Cuarzo rosa", 4, propiedades="Aroma rosas. " + PROPIEDADES["Cuarzo rosa"])],
    },
    {
        "categoria": "Inciensos y limpieza energética", "nombre": "Kit de inciensos orgánicos",
        "descripcion": "Caja con 20 varitas de incienso orgánico de combustión lenta y una base de madera.",
        "precio_base": "22.00", "material": "Incienso orgánico", "medidas": "20 varitas",
        "variantes": [v("Palo santo", 6, propiedades=None), v("Lavanda", 5), v("Sándalo", 5), v("Ruda", 4)],
    },
    {
        "categoria": "Inciensos y limpieza energética", "nombre": "Spray áurico",
        "descripcion": "Spray de 60 ml con agua floral, aceites esenciales y chips de cuarzo para "
                       "aromatizar y armonizar tus espacios.",
        "precio_base": "25.00", "material": "Agua floral y aceites esenciales", "medidas": "60 ml",
        "existencias": 6,
    },
    {
        "categoria": "Boxes y kits", "nombre": "Box de limpieza energética",
        "descripcion": "Caja de regalo con palo santo, incienso, una vela, un cuarzo rodado y una tarjeta "
                       "con el ritual paso a paso.",
        "precio_base": "55.00", "material": "Varios", "medidas": "Caja de 15 × 15 cm",
        "variantes": [v("Cuarzo rosa", 3), v("Amatista", 3), v("Citrino", 2), v("Turmalina negra", 2)],
    },
    {
        "categoria": "Decoración y amuletos", "nombre": "Atrapasol de cristal",
        "descripcion": "Atrapasol con prismas de cristal y cuentas de piedra natural. Al recibir la luz "
                       "del sol proyecta arcoíris en tu espacio.",
        "precio_base": "45.00", "material": "Cristal, piedra natural y alambre", "medidas": "40 cm de largo",
        "existencias": 4,
    },
    {
        "categoria": "Decoración y amuletos", "nombre": "Atrapasueños de macramé",
        "descripcion": "Atrapasueños tejido a mano en macramé con plumas y un cuarzo blanco al centro.",
        "precio_base": "38.00", "material": "Hilo de algodón, plumas y cuarzo", "medidas": "15 cm de diámetro",
        "existencias": 3,
    },
]


def cargar(db, aplicar: bool) -> None:
    categorias = {c.nombre: c.id for c in db.query(Categoria).all()}
    existentes = {nombre for (nombre,) in db.query(Producto.nombre).all()}
    creados = 0
    for datos in PRODUCTOS:
        nombre = datos["nombre"]
        variantes = datos.get("variantes", [])
        if nombre in existentes:
            print(f"  = ya existe, se salta: {nombre}")
            continue
        if datos["categoria"] not in categorias:
            raise SystemExit(f"No existe la categoría {datos['categoria']!r} (¿se cargaron las 7?).")
        resumen = ", ".join(x["nombre"] for x in variantes) or "variante única"
        print(f"  + {nombre} ({datos['categoria']}, S/ {datos['precio_base']}): {resumen}")
        creados += 1
        if not aplicar:
            continue

        campos = {k: val for k, val in datos.items() if k not in ("categoria", "variantes")}
        producto = crear_producto(db, ProductoCrear(categoria_id=categorias[datos["categoria"]], **campos))
        if variantes:
            # La variante "Única" se reutiliza como primera piedra o aroma; las demás se agregan.
            unica, *resto = variantes
            for campo, valor in unica.items():
                setattr(producto.variantes[0], campo, Decimal(valor) if campo == "precio" and valor else valor)
            for extra in resto:
                precio = Decimal(extra["precio"]) if extra["precio"] else None
                db.add(Variante(producto_id=producto.id, **{**extra, "precio": precio}))
            db.commit()
    accion = "Creados" if aplicar else "Se crearían"
    print(f"{accion} {creados} productos (despublicados, sin fotos).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aplicar", action="store_true", help="escribe en la base (sin esto solo simula)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        print("MODO:", "APLICAR (escribe en la base)" if args.aplicar else "SIMULACIÓN (no escribe nada)")
        cargar(db, args.aplicar)
    finally:
        db.close()


if __name__ == "__main__":
    main()
