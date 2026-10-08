"""Carga el Catálogo 2025 REAL de Akash Store (T-01 #3) desde scripts/data/catalogo_akashstore_2025.xlsx.

- Productos DESPUBLICADOS: la propietaria revisa y publica desde el panel (HU016).
- Antes de escribir se revisa la hoja con las reglas de scripts/cargar_catalogo.py: si hay errores, no se carga nada.
- Los productos sin precio en la hoja (pendientes de confirmar con ella) se saltan y se listan.
- Existencias: si la hoja tiene una columna 'existencias' se usa; si no, quedan en 0 ("Agotado") y se
  ajustan desde el panel (HU015). Con --existencias N las variantes sin dato arrancan con N.
- Fotos (opcional): --fotos CARPETA con una subcarpeta por producto, con el nombre del producto en
  minúsculas y con guiones (ej. collar-de-amatista/). Las fotos pasan por la misma subida de la API.
- Idempotente: si ya existe un producto con el mismo nombre, lo salta (y avisa si su precio difiere).

Uso (desde backend/, con DATABASE_URL en .env):
    python -m scripts.seed_catalogo                         # simulación: no escribe nada
    python -m scripts.seed_catalogo --fotos C:\\fotos        # simulación, y lista qué fotos subiría
    python -m scripts.seed_catalogo --aplicar               # carga en la base (pide confirmación)
"""
import argparse
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import inspect

from app import models  # noqa: F401  registra todos los modelos para las relaciones
from app.database import SessionLocal
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.variante import Variante
from app.schemas.producto import ProductoCrear
from app.services import imagenes as servicio_imagenes
from app.services.productos import crear_producto
from scripts.catalogo_datos import HOJA_POR_DEFECTO, VARIANTE_UNICA, leer_catalogo, slug

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


def _stock(variante: dict, por_defecto: int) -> int:
    return variante["existencias"] if variante["existencias"] is not None else por_defecto


def _crear(db, categorias: dict, datos: dict, existencias: int) -> Producto:
    campos = {k: datos[k] for k in ("nombre", "descripcion", "material", "medidas", "precio_base", "es_pieza_natural")}
    variantes = datos["variantes"]
    unica_sola = len(variantes) == 1 and variantes[0]["nombre"] == VARIANTE_UNICA
    producto = crear_producto(db, ProductoCrear(
        categoria_id=categorias[datos["categoria"]],
        existencias=_stock(variantes[0], existencias) if unica_sola else existencias,
        **campos,
    ))
    if unica_sola:
        return producto  # sin piedras ni aromas: basta la variante "Única" que ya trae el producto
    # La variante "Única" se reutiliza como primera piedra o aroma; las demás se agregan (HU027).
    primera, *resto = variantes
    unica = producto.variantes[0]
    unica.nombre, unica.precio, unica.propiedades = primera["nombre"], primera["precio"], primera["propiedades"]
    unica.existencias = _stock(primera, existencias)
    for extra in resto:
        db.add(Variante(producto_id=producto.id, nombre=extra["nombre"], precio=extra["precio"],
                        propiedades=extra["propiedades"], existencias=_stock(extra, existencias)))
    db.commit()
    db.refresh(producto)
    return producto


def _subir_fotos(db, producto: Producto | None, nombre: str, carpeta: Path, aplicar: bool) -> int:
    destino = carpeta / slug(nombre)
    fotos = sorted(f for f in destino.iterdir() if f.suffix.lower() in EXTENSIONES) if destino.is_dir() else []
    if not fotos:
        print(f"      sin fotos (no hay fotos en {destino.name}/)")
        return 0
    if producto is not None and producto.imagenes:
        print("      ya tiene fotos: no se suben otras")
        return 0
    fotos = fotos[: servicio_imagenes.MAX_FOTOS]
    print(f"      {len(fotos)} foto(s) en {destino.name}/")
    if not aplicar:
        return len(fotos)
    subidas = 0
    for foto in fotos:
        try:
            servicio_imagenes.subir_imagen(db, producto.id, foto.read_bytes())
            subidas += 1
        except HTTPException as error:  # foto muy grande, formato no permitido, etc.
            print(f"      !! no se subió {foto.name}: {error.detail}")
    return subidas


def cargar(db, aplicar: bool, existencias: int = 0, ruta_hoja: Path = HOJA_POR_DEFECTO,
           carpeta_fotos: Path | None = None) -> None:
    categorias = {c.nombre: c.id for c in db.query(Categoria).all()}
    existentes = {p.nombre: p for p in db.query(Producto).all()}
    creados, sin_precio, fotos = 0, [], 0
    for datos in leer_catalogo(ruta_hoja):
        nombre = datos["nombre"]
        if datos["precio_base"] is None:
            sin_precio.append(nombre)
            print(f"  !! sin precio en la hoja, se salta: {nombre}")
            continue
        if nombre in existentes:
            producto = existentes[nombre]
            aviso = ""
            if producto.precio_base != datos["precio_base"]:
                aviso = (f"  !! en la base cuesta S/ {producto.precio_base} y en la hoja S/ {datos['precio_base']} "
                         "(¿viene del seed de ejemplo?)")
            print(f"  = ya existe, se salta: {nombre}{aviso}")
        else:
            if datos["categoria"] not in categorias:
                raise SystemExit(f"No existe la categoría {datos['categoria']!r} (¿se cargaron las 7?).")
            variantes = datos["variantes"]
            resumen = ", ".join(v["nombre"] for v in variantes) if len(variantes) > 1 else "variante única"
            print(f"  + {nombre} ({datos['categoria']}, S/ {datos['precio_base']}): {resumen}")
            creados += 1
            producto = _crear(db, categorias, datos, existencias) if aplicar else None
        if carpeta_fotos is not None:
            fotos += _subir_fotos(db, producto, nombre, carpeta_fotos, aplicar)
    accion = "Creados" if aplicar else "Se crearían"
    print(f"{accion} {creados} productos (despublicados, existencias {existencias}).")
    if carpeta_fotos is not None:
        print(f"{'Subidas' if aplicar else 'Se subirían'} {fotos} fotos.")
    if sin_precio:
        print(f"Pendientes de precio ({len(sin_precio)}): confirmar con la propietaria (T-01 #2).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aplicar", action="store_true", help="escribe en la base (sin esto solo simula)")
    parser.add_argument("--existencias", type=int, default=0, help="existencias iniciales de cada variante nueva")
    parser.add_argument("--fotos", type=Path, help="carpeta con una subcarpeta de fotos por producto")
    parser.add_argument("--hoja", type=Path, default=HOJA_POR_DEFECTO, help="Excel del catálogo (por defecto el del repo)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        servidor = db.get_bind().url.host or "(base local)"
        print("Base de datos:", servidor)
        if not inspect(db.get_bind()).has_table("categoria"):
            raise SystemExit(
                "Esta base no tiene las tablas del proyecto (¿DATABASE_URL de backend/.env está vacío o apunta a un "
                "archivo local?). Pide las credenciales de Supabase en el gestor compartido. No se escribió nada."
            )
        print("MODO:", "APLICAR (escribe en la base)" if args.aplicar else "SIMULACIÓN (no escribe nada)")
        if args.aplicar and input("Escribe SI para continuar: ").strip() != "SI":
            raise SystemExit("Cancelado: no se escribió nada.")
        cargar(db, args.aplicar, args.existencias, args.hoja, args.fotos)
    finally:
        db.close()


if __name__ == "__main__":
    main()
