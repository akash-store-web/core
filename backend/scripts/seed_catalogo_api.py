"""Carga el catálogo real usando la API desplegada, con TU usuario del panel (no necesita DATABASE_URL).

Hace lo mismo que seed_catalogo.py, pero por HTTP: crea los productos despublicados, sus variantes
y, opcionalmente, sube fotos. Si un producto ya existe con el mismo nombre, lo salta.
Por defecto SIMULA: inicia sesión y lee, pero no escribe nada.

Uso (desde backend/, con el entorno virtual activo):
    python -m scripts.seed_catalogo_api                       # simulación
    python -m scripts.seed_catalogo_api --fotos D:\\fotos      # simulación + lista de fotos
    python -m scripts.seed_catalogo_api --aplicar             # escribe en producción (pide confirmación)
"""
import argparse
import getpass
from pathlib import Path

import httpx

from scripts.catalogo_datos import HOJA_POR_DEFECTO, VARIANTE_UNICA, leer_catalogo, slug

API_POR_DEFECTO = "https://akash-store-api.onrender.com"
TIPOS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MAX_FOTOS = 5


class ErrorApi(Exception):
    pass


def detalle(r) -> str:
    try:
        return str(r.json().get("detail", r.text))
    except Exception:
        return r.text


class Api:
    def __init__(self, base: str, email: str, password: str):
        self.http = httpx.Client(base_url=base.rstrip("/"), timeout=120)
        self.email, self.password = email, password
        self.iniciar_sesion()

    def iniciar_sesion(self) -> None:
        r = self.http.post("/auth/login", json={"email": self.email, "password": self.password})
        if r.status_code != 200:
            raise SystemExit(f"No se pudo iniciar sesión ({r.status_code}): {detalle(r)}")
        self.http.headers["Authorization"] = "Bearer " + r.json()["access_token"]

    def pedir(self, metodo: str, ruta: str, **datos):
        r = self.http.request(metodo, ruta, **datos)
        if r.status_code == 401:  # el token dura 30 min: se renueva solo
            self.iniciar_sesion()
            r = self.http.request(metodo, ruta, **datos)
        return r

    def exigir(self, metodo: str, ruta: str, **datos):
        r = self.pedir(metodo, ruta, **datos)
        if r.status_code >= 400:
            raise ErrorApi(f"{metodo} {ruta} respondió {r.status_code}: {detalle(r)}")
        return r.json() if r.content else None


def _stock(variante: dict, por_defecto: int) -> int:
    return variante["existencias"] if variante["existencias"] is not None else por_defecto


def _cuerpo_variante(variante: dict, por_defecto: int) -> dict:
    return {
        "nombre": variante["nombre"],
        "precio": str(variante["precio"]) if variante["precio"] is not None else None,
        "existencias": _stock(variante, por_defecto),
        "propiedades": variante["propiedades"],
    }


def crear(api: Api, categorias: dict, datos: dict, existencias: int) -> int:
    variantes = datos["variantes"]
    unica_sola = len(variantes) == 1 and variantes[0]["nombre"] == VARIANTE_UNICA
    cuerpo = {
        "categoria_id": categorias[datos["categoria"]],
        "nombre": datos["nombre"],
        "descripcion": datos["descripcion"],
        "precio_base": str(datos["precio_base"]),
        "es_pieza_natural": datos["es_pieza_natural"],
        "existencias": _stock(variantes[0], existencias) if unica_sola else existencias,
    }
    for campo in ("material", "medidas"):
        if datos[campo]:
            cuerpo[campo] = datos[campo]
    producto_id = api.exigir("POST", "/admin/productos", json=cuerpo)["id"]
    if unica_sola:
        return producto_id  # sin piedras ni aromas: basta la variante "Única" que ya trae el producto
    # La variante "Única" se renombra como primera piedra o aroma; las demás se agregan (HU027).
    primera, *resto = variantes
    unica = api.exigir("GET", f"/admin/productos/{producto_id}/variantes")[0]
    api.exigir("PUT", f"/admin/productos/{producto_id}/variantes/{unica['id']}",
               json=_cuerpo_variante(primera, existencias))
    for extra in resto:
        api.exigir("POST", f"/admin/productos/{producto_id}/variantes", json=_cuerpo_variante(extra, existencias))
    return producto_id


def subir_fotos(api: Api, producto_id: int | None, nombre: str, carpeta: Path, aplicar: bool) -> int:
    destino = carpeta / slug(nombre)
    fotos = sorted(f for f in destino.iterdir() if f.suffix.lower() in TIPOS) if destino.is_dir() else []
    if not fotos:
        print(f"      sin fotos (no hay fotos en {destino.name}/)")
        return 0
    fotos = fotos[:MAX_FOTOS]
    print(f"      {len(fotos)} foto(s) en {destino.name}/")
    if not aplicar or producto_id is None:
        return len(fotos)
    subidas = 0
    for foto in fotos:
        r = api.pedir("POST", f"/admin/productos/{producto_id}/imagenes",
                      files={"foto": (foto.name, foto.read_bytes(), TIPOS[foto.suffix.lower()])})
        if r.status_code == 201:
            subidas += 1
        else:
            print(f"      !! no se subió {foto.name}: {detalle(r)}")
    return subidas


def cargar(api: Api, aplicar: bool, existencias: int, hoja: Path, carpeta: Path | None) -> None:
    categorias = {c["nombre"]: c["id"] for c in api.exigir("GET", "/admin/categorias")}
    existentes = {p["nombre"]: p for p in api.exigir("GET", "/admin/productos")}
    creados, fotos, sin_precio, fallos = 0, 0, [], []
    for datos in leer_catalogo(hoja):
        nombre = datos["nombre"]
        if datos["precio_base"] is None:
            sin_precio.append(nombre)
            print(f"  !! sin precio en la hoja, se salta: {nombre}")
            continue
        existente = existentes.get(nombre)
        if existente:
            print(f"  = ya existe, se salta: {nombre} (en la base cuesta S/ {existente['precio_base']}, "
                  f"en la hoja S/ {datos['precio_base']})")
            if carpeta and existente["foto_generica"]:  # solo si todavía no tiene fotos reales
                fotos += subir_fotos(api, existente["id"], nombre, carpeta, aplicar)
            continue
        if datos["categoria"] not in categorias:
            print(f"  !! no existe la categoría {datos['categoria']!r}: se salta {nombre}")
            fallos.append(nombre)
            continue
        variantes = datos["variantes"]
        resumen = ", ".join(v["nombre"] for v in variantes) if len(variantes) > 1 else "variante única"
        print(f"  + {nombre} ({datos['categoria']}, S/ {datos['precio_base']}): {resumen}")
        producto_id = None
        if aplicar:
            try:
                producto_id = crear(api, categorias, datos, existencias)
            except ErrorApi as error:
                print(f"  !! FALLÓ {nombre}: {error}")
                fallos.append(nombre)
                continue
        creados += 1
        if carpeta:
            fotos += subir_fotos(api, producto_id, nombre, carpeta, aplicar)
    print(f"{'Creados' if aplicar else 'Se crearían'} {creados} productos (despublicados, existencias {existencias}).")
    if carpeta:
        print(f"{'Subidas' if aplicar else 'Se subirían'} {fotos} fotos.")
    if sin_precio:
        print(f"Pendientes de precio ({len(sin_precio)}): confirmar con la propietaria.")
    if fallos:
        print(f"Con problemas ({len(fallos)}): {', '.join(fallos)}. Revisa cada uno en el panel antes de repetir.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aplicar", action="store_true", help="escribe en la API (sin esto solo simula)")
    parser.add_argument("--existencias", type=int, default=0, help="existencias iniciales de cada variante nueva")
    parser.add_argument("--fotos", type=Path, help="carpeta con una subcarpeta de fotos por producto")
    parser.add_argument("--hoja", type=Path, default=HOJA_POR_DEFECTO, help="Excel del catálogo (por defecto el del repo)")
    parser.add_argument("--api", default=API_POR_DEFECTO, help="URL de la API")
    parser.add_argument("--email", help="correo de tu usuario del panel")
    args = parser.parse_args()

    email = args.email or input("Correo de tu usuario del panel: ").strip()
    password = getpass.getpass("Contraseña (no se ve al escribir): ")
    print(f"Conectando con {args.api} (si el servidor estaba dormido puede tardar cerca de un minuto)...")
    api = Api(args.api, email, password)
    print("Sesión iniciada.")
    print("MODO:", "APLICAR (escribe en la API real)" if args.aplicar else "SIMULACIÓN (no escribe nada)")
    if args.aplicar and input("Escribe SI para continuar: ").strip() != "SI":
        raise SystemExit("Cancelado: no se escribió nada.")
    try:
        cargar(api, args.aplicar, args.existencias, args.hoja, args.fotos)
    except ValueError as error:  # la hoja tiene errores: no se carga nada
        raise SystemExit(str(error))
    except ErrorApi as error:
        raise SystemExit(f"Error de la API: {error}")


if __name__ == "__main__":
    main()
