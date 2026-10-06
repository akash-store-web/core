"""Genera la colección y los entornos de Postman en docs/postman/ y valida que cubran TODAS las rutas.

Uso (desde backend/):  python -m scripts.generar_postman
Si agregas una ruta a la API y no la agregas aquí, el script falla y dice cuál falta.
No se conecta a ninguna base: solo lee las rutas de la app.
"""
import json
import os
import re
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("JWT_SECRET", "x" * 40)
from app.main import app  # noqa: E402

SALIDA = Path(__file__).resolve().parents[2] / "docs" / "postman"
ESCRIBE = "⚠️ Escribe en la base del entorno elegido."


def test(*lineas):
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": list(lineas)}}]


def codigo(n):
    return test(f'pm.test("Responde {n}", () => pm.response.to.have.status({n}));')


def req(nombre, metodo, ruta, cuerpo=None, descripcion="", eventos=None, publico=False, formdata=None, query=None):
    url_raw = "{{baseUrl}}" + ruta
    url = {"raw": url_raw, "host": ["{{baseUrl}}"], "path": [p for p in ruta.split("?")[0].strip("/").split("/")]}
    if query:
        url["query"] = query
        url["raw"] += "?" + "&".join(f"{q['key']}={q['value']}" for q in query)
    r = {"method": metodo, "header": [], "url": url, "description": descripcion}
    if cuerpo is not None:
        r["header"].append({"key": "Content-Type", "value": "application/json"})
        r["body"] = {"mode": "raw", "raw": json.dumps(cuerpo, ensure_ascii=False, indent=2),
                     "options": {"raw": {"language": "json"}}}
    if formdata is not None:
        r["body"] = {"mode": "formdata", "formdata": formdata}
    if publico:
        r["auth"] = {"type": "noauth"}
    item = {"name": nombre, "request": r}
    if eventos:
        item["event"] = eventos
    return item


def carpeta(nombre, descripcion, items, publico=False):
    c = {"name": nombre, "description": descripcion, "item": items}
    if publico:
        c["auth"] = {"type": "noauth"}
    return c


guardar_token = test(
    'pm.test("Login correcto", () => pm.response.to.have.status(200));',
    'const datos = pm.response.json();',
    'pm.collectionVariables.set("token", datos.access_token);',
    'console.log("Token guardado en la variable {{token}} (dura 30 minutos)");',
)

guardar = lambda var, campo="id", status=201: test(  # noqa: E731
    f'pm.test("Responde {status}", () => pm.response.to.have.status({status}));',
    f'if (pm.response.code === {status}) pm.collectionVariables.set("{var}", pm.response.json().{campo});',
)

items = [
    carpeta("0. Estado", "Ejecútalo primero: Render gratuito se duerme y la primera respuesta puede tardar ~50 s.", [
        req("Health", "GET", "/health", descripcion="Debe responder {\"status\": \"ok\"}.", eventos=codigo(200), publico=True),
    ], publico=True),
    carpeta("1. Auth", "Primero ejecuta **Login**: guarda el token y todas las rutas del panel lo usan solas.", [
        req("Login", "POST", "/auth/login", {"email": "{{email}}", "password": "{{password}}"},
            "Usa las variables `email` y `password` del entorno. Guarda `access_token` en `{{token}}`.",
            guardar_token, publico=True),
        req("Login con credenciales inválidas (401)", "POST", "/auth/login",
            {"email": "{{email}}", "password": "incorrecta"}, "Debe responder 401 sin decir qué campo falló.",
            codigo(401), publico=True),
        req("Recuperar contraseña", "POST", "/auth/recuperar", {"email": "{{email}}"},
            "Siempre 202, exista o no el correo. ⚠️ Si el correo existe, Brevo envía un correo real.",
            codigo(202), publico=True),
        req("Restablecer contraseña", "POST", "/auth/restablecer",
            {"token": "<pega aquí el token del enlace del correo>", "nueva_contrasena": "nueva-clave-segura"},
            "El token sale del enlace `.../restablecer?token=...`. Vence en 30 min y sirve una vez. " + ESCRIBE,
            publico=True),
        req("Cambiar contraseña (con sesión)", "PUT", "/auth/contrasena",
            {"actual": "{{password}}", "nueva": "nueva-clave-segura"},
            "⚠️ Cambia la contraseña real de la cuenta del entorno. Después actualiza `password` en el entorno."),
    ]),
    carpeta("2. Catálogo (público)", "Sin login. Solo productos publicados; nunca muestra existencias exactas.", [
        req("Catálogo", "GET", "/catalogo", descripcion="Tarjetas del catálogo. `foto_principal` nunca es null.",
            eventos=test('pm.test("Responde 200", () => pm.response.to.have.status(200));',
                         'const lista = pm.response.json();',
                         'pm.test("Toda tarjeta trae foto_principal", () => lista.forEach(p => pm.expect(p.foto_principal).to.be.a("string")));',
                         'if (lista.length) pm.collectionVariables.set("producto_id", lista[0].id);'),
            publico=True),
        req("Catálogo filtrado", "GET", "/catalogo", publico=True, eventos=codigo(200),
            query=[{"key": "categoria_id", "value": "2", "description": "2 = Pulseras"},
                   {"key": "q", "value": "cuarzo", "description": "búsqueda por nombre"}]),
        req("Categorías del catálogo", "GET", "/catalogo/categorias", publico=True, eventos=codigo(200)),
        req("Ficha de producto", "GET", "/catalogo/{{producto_id}}",
            descripcion="`tiene_variantes:false` = no mostrar selector. 404 si está despublicado.",
            publico=True, eventos=codigo(200)),
    ], publico=True),
    carpeta("3. Carrito y envío (público)", "Para el carrito y el checkout, sin login.", [
        req("Validar carrito", "POST", "/carrito/validar",
            {"items": [{"variante_id": "{{variante_id}}", "cantidad": 2}, {"variante_id": 1, "cantidad": 1}]},
            "Revisa cada ítem contra el stock real. Siempre 200; `valido: true` = se puede pasar al checkout. "
            "Estados por ítem: ok, stock_insuficiente, agotado, no_disponible.",
            test('pm.test("Responde 200", () => pm.response.to.have.status(200));',
                 'pm.test("Trae valido y total", () => { const d = pm.response.json(); pm.expect(d).to.have.property("valido"); pm.expect(d.total).to.be.a("string"); });'),
            publico=True),
        req("Distritos con costo", "GET", "/envio/distritos", publico=True, eventos=codigo(200)),
        req("Costo de envío de un distrito", "GET", "/envio/costo", publico=True, eventos=codigo(200),
            query=[{"key": "distrito_id", "value": "{{distrito_id}}"}]),
    ], publico=True),
    carpeta("4. Panel: productos 🔒", "Requiere haber ejecutado **1. Auth / Login**.", [
        req("Categorías (desplegable)", "GET", "/admin/categorias", eventos=codigo(200)),
        req("Listado del panel", "GET", "/admin/productos", eventos=codigo(200),
            query=[{"key": "q", "value": "", "description": "búsqueda por nombre (opcional)"},
                   {"key": "categoria_id", "value": "", "description": "opcional"}]),
        req("Crear producto", "POST", "/admin/productos", {
            "categoria_id": 4, "nombre": "Anillo de prueba QA", "descripcion": "Producto creado desde Postman para pruebas.",
            "precio_base": "40.00", "material": "Plata 925", "medidas": "Piedra de 8 × 10 mm",
            "es_pieza_natural": True, "existencias": 3},
            "Nace despublicado y con la variante \"Única\". Guarda el id en `{{producto_id}}`. " + ESCRIBE
            + " No hay borrado de productos: despublícalo al terminar.",
            guardar("producto_id")),
        req("Crear producto sin obligatorios (422)", "POST", "/admin/productos", {"nombre": "Incompleto"},
            "Debe responder 422 listando categoria_id, descripcion y precio_base.", codigo(422)),
        req("Obtener producto", "GET", "/admin/productos/{{producto_id}}", eventos=codigo(200)),
        req("Editar producto", "PUT", "/admin/productos/{{producto_id}}", {
            "categoria_id": 4, "nombre": "Anillo de prueba QA", "descripcion": "Descripción editada desde Postman.",
            "precio_base": "42.00", "material": "Plata 925", "medidas": "Piedra de 8 × 10 mm", "es_pieza_natural": True},
            "No cambia `publicado`. " + ESCRIBE, codigo(200)),
        req("Publicar", "PATCH", "/admin/productos/{{producto_id}}/publicado", {"publicado": True},
            "409 si falta variante, o foto real cuando PUBLICAR_EXIGE_FOTO=true. " + ESCRIBE),
        req("Despublicar", "PATCH", "/admin/productos/{{producto_id}}/publicado", {"publicado": False},
            "Siempre se permite. " + ESCRIBE, codigo(200)),
    ]),
    carpeta("5. Panel: variantes 🔒", "Usa `{{producto_id}}` y `{{variante_id}}`.", [
        req("Variantes del producto", "GET", "/admin/productos/{{producto_id}}/variantes",
            eventos=test('pm.test("Responde 200", () => pm.response.to.have.status(200));',
                         'const v = pm.response.json();',
                         'if (v.length) pm.collectionVariables.set("variante_id", v[0].id);')),
        req("Crear variante", "POST", "/admin/productos/{{producto_id}}/variantes",
            {"nombre": "Turmalina negra", "precio": None, "existencias": 2, "propiedades": "Se le atribuye protección."},
            "`precio: null` hereda el precio_base. " + ESCRIBE, guardar("variante_id")),
        req("Editar variante (precio propio)", "PUT", "/admin/productos/{{producto_id}}/variantes/{{variante_id}}",
            {"nombre": "Amatista", "precio": "45.00", "existencias": 3, "propiedades": "Se le atribuye calma."},
            "Para la primera piedra, renombra la variante \"Única\". " + ESCRIBE, codigo(200)),
        req("Stock: botón −1", "PATCH", "/admin/variantes/{{variante_id}}/stock", {"cambio": -1},
            "Respuesta ligera. 409 si quedaría negativo. " + ESCRIBE, codigo(200)),
        req("Stock: cantidad exacta", "PATCH", "/admin/variantes/{{variante_id}}/stock", {"existencias": 10},
            ESCRIBE, codigo(200)),
        req("Eliminar variante", "DELETE", "/admin/productos/{{producto_id}}/variantes/{{variante_id}}",
            descripcion="204. 409 si es la última del producto o tiene pedidos. " + ESCRIBE),
    ]),
    carpeta("6. Panel: fotos 🔒", "JPG, PNG o WEBP; máx. 5 MB y 5 fotos por producto.", [
        req("Subir foto", "POST", "/admin/productos/{{producto_id}}/imagenes",
            descripcion="En Body → form-data, elige el archivo en el campo `foto` (tipo File). La primera queda como principal. "
                        + ESCRIBE + " (y en Supabase Storage)",
            formdata=[{"key": "foto", "type": "file", "src": []}], eventos=guardar("imagen_id")),
        req("Marcar como principal", "PATCH", "/admin/productos/{{producto_id}}/imagenes/{{imagen_id}}/principal",
            descripcion=ESCRIBE, eventos=codigo(200)),
        req("Eliminar foto", "DELETE", "/admin/productos/{{producto_id}}/imagenes/{{imagen_id}}",
            descripcion="204. Si era la principal, pasa a serlo la siguiente. " + ESCRIBE, eventos=codigo(204)),
    ]),
    carpeta("7. Panel: envíos 🔒", "Zonas con costo y distritos asignados (HU026).", [
        req("Zonas de envío", "GET", "/admin/zonas-envio", eventos=codigo(200)),
        req("Crear zona", "POST", "/admin/zonas-envio", {"nombre": "Zona de prueba QA", "costo": "10.00", "activa": True},
            ESCRIBE, guardar("zona_id")),
        req("Editar zona", "PUT", "/admin/zonas-envio/{{zona_id}}", {"nombre": "Zona de prueba QA", "costo": "12.00", "activa": False},
            "`activa: false` deja de atenderla sin borrarla. " + ESCRIBE, codigo(200)),
        req("Asignar distritos a la zona", "PUT", "/admin/zonas-envio/{{zona_id}}/distritos", {"distrito_ids": ["{{distrito_id}}"]},
            ESCRIBE, codigo(200)),
        req("Distritos", "GET", "/admin/distritos", eventos=codigo(200),
            query=[{"key": "sin_zona", "value": "true", "description": "solo los que no tienen cobertura"}]),
        req("Crear distrito", "POST", "/admin/distritos", {"nombre": "Distrito de prueba QA", "zona_envio_id": None},
            "409 si el nombre ya existe. " + ESCRIBE, guardar("distrito_id")),
        req("Editar distrito (quitar cobertura)", "PUT", "/admin/distritos/{{distrito_id}}",
            {"nombre": "Distrito de prueba QA", "zona_envio_id": None}, ESCRIBE, codigo(200)),
    ]),
    carpeta("8. Panel: pedidos 🔒", "Bandeja y detalle de pedidos (HU017). Solo lectura.", [
        req("Bandeja de pedidos", "GET", "/admin/pedidos",
            descripcion="Del más reciente al más antiguo. Estados: pendiente_pago, por_validar, confirmado, "
                        "rechazado, enviado, entregado, vencido.",
            eventos=test('pm.test("Responde 200", () => pm.response.to.have.status(200));',
                         'const p = pm.response.json();',
                         'if (p.length) pm.collectionVariables.set("pedido_id", p[0].id);'),
            query=[{"key": "estado", "value": "", "description": "opcional, p. ej. por_validar"},
                   {"key": "q", "value": "", "description": "número, nombre o teléfono (opcional)"}]),
        req("Detalle del pedido", "GET", "/admin/pedidos/{{pedido_id}}",
            descripcion="Clienta, ítems con precio histórico, totales, comprobante e historial de estados.",
            eventos=codigo(200)),
    ]),
]

# "{{distrito_id}}" dentro de una lista JSON debe ir sin comillas para que sea número
for c in items:
    for it in c["item"]:
        body = it["request"].get("body", {})
        if body.get("mode") == "raw":
            body["raw"] = body["raw"].replace('"{{distrito_id}}"', "{{distrito_id}}").replace('"{{variante_id}}"', "{{variante_id}}")

coleccion = {
    "info": {
        "name": "Akash Store API",
        "description": "Colección de pruebas del backend de Akash Store. Guía completa: `docs/API.md`.\n\n"
                       "1. Importa la colección y un entorno (Render o Local).\n"
                       "2. En el entorno, completa `email` y `password` (valor actual, NO el inicial: así no se exporta).\n"
                       "3. Ejecuta **1. Auth / Login**: el token se guarda solo.\n\n"
                       "⚠️ El entorno Render usa la base real de Supabase: las peticiones marcadas escriben datos reales. "
                       "Usa nombres con 'QA' y despublica lo que crees.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]},
    "variable": [{"key": k, "value": v} for k, v in
                 [("token", ""), ("producto_id", "1"), ("variante_id", "1"), ("imagen_id", "1"), ("zona_id", "1"), ("distrito_id", "1"), ("pedido_id", "1")]],
    "item": items,
}


def entorno(nombre, base):
    return {
        "name": f"Akash Store - {nombre}",
        "values": [
            {"key": "baseUrl", "value": base, "type": "default", "enabled": True},
            {"key": "email", "value": "", "type": "default", "enabled": True},
            {"key": "password", "value": "", "type": "secret", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }


# --- Validación: todas las rutas de la API están en la colección ---
esperadas = {(m.upper(), re.sub(r"\{[^}]+\}", "{}", ruta)) for ruta, ops in app.openapi()["paths"].items() for m in ops}
cubiertas = set()
for c in items:
    for it in c["item"]:
        r = it["request"]
        ruta = "/" + "/".join(r["url"]["path"])
        cubiertas.add((r["method"], re.sub(r"\{\{[^}]+\}\}", "{}", ruta)))
faltan = esperadas - cubiertas
sobran = cubiertas - esperadas
assert not faltan, f"Faltan en la colección: {sorted(faltan)}"
assert not sobran, f"Rutas que no existen en la API: {sorted(sobran)}"

os.makedirs(SALIDA, exist_ok=True)
for nombre, data in [("AkashStore.postman_collection.json", coleccion),
                     ("AkashStore-Render.postman_environment.json", entorno("Render", "https://akash-store-api.onrender.com")),
                     ("AkashStore-Local.postman_environment.json", entorno("Local", "http://localhost:8000"))]:
    with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
total = sum(len(c["item"]) for c in items)
print(f"OK: {total} peticiones, {len(esperadas)} rutas de la API cubiertas")
