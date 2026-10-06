# API de Akash Store — guía para el frontend

Backend FastAPI. Esta guía resume el contrato; la referencia interactiva siempre actualizada está en **`/docs`** (Swagger).

| Entorno | URL base | Swagger |
|---|---|---|
| Producción (Render) | `https://akash-store-api.onrender.com` | [/docs](https://akash-store-api.onrender.com/docs) |
| Local | `http://localhost:8000` | [/docs](http://localhost:8000/docs) |

**Postman.** En `docs/postman/` están la colección (`AkashStore.postman_collection.json`) y dos entornos (Render y Local). En Postman: **Import** → arrastra los tres archivos → elige el entorno → completa `email` y `password` en la columna *Current value* (así no se exportan) → ejecuta **0. Estado** y luego **1. Auth / Login**: el token se guarda solo y las carpetas del panel lo usan. Las peticiones marcadas con ⚠️ escriben en la base del entorno elegido (en Render, la real).

En el frontend la URL base viene de `VITE_API_URL`. Render gratuito "duerme" tras 15 min sin uso: la primera petición puede tardar ~50 s; muestren un estado de carga y no lo traten como error.

---

## Convenciones

**Autenticación.** Las rutas `/admin/*` y `PUT /auth/contrasena` exigen el header:

```
Authorization: Bearer <access_token>
```

El token dura **30 minutos**. Si cualquier ruta responde `401`, borren el token y redirijan al login (HU023: "la sesión se cierra por inactividad"). El catálogo, `/envio/*` y el resto de `/auth/*` son públicos.

**Montos.** Precios y costos llegan como **texto con 2 decimales**: `"25.00"`. No se usan números para no perder centavos. Para mostrarlos:

```js
const soles = (monto) => `S/ ${Number(monto).toFixed(2)}`;
```

Al enviar montos, manden texto (`"25.00"`) o número (`25`); máximo 2 decimales.

**Errores.** Siempre vienen en `detail`:

| Código | Significado | Forma de `detail` |
|---|---|---|
| 400 | Petición no válida (p. ej. enlace vencido) | texto |
| 401 | Sin token, token vencido o credenciales inválidas | texto |
| 404 | No existe (o, en el catálogo, no está publicado) | texto |
| 409 | Choca con una regla del negocio | texto, listo para mostrar |
| 413 / 415 | Foto muy grande / formato no permitido | texto |
| 422 | Validación de campos | **lista** (ver abajo) o texto |
| 502 | Falló un servicio externo (Storage) | texto |

Un `422` de validación trae una lista; `loc[1]` es el campo con el problema:

```json
{"detail": [{"type": "missing", "loc": ["body", "precio_base"], "msg": "Field required"}]}
```

```js
const mensaje = (detail) => Array.isArray(detail) ? detail.map(e => `${e.loc.at(-1)}: ${e.msg}`).join("\n") : detail;
```

**Fotos que aún no existen.** `foto_principal` **nunca viene vacía**: si el producto no tiene fotos reales, el backend envía la URL de la imagen genérica (800×800, en Supabase Storage) y `foto_generica: true`. Úsenla directo en el `<img>`. Usos de la bandera:
- En el panel, mostrar un aviso "Falta subir fotos" cuando `foto_generica` sea `true`.
- `imagenes` (lista de fotos reales) sí puede venir vacía: en la galería de la ficha, si está vacía, muestren solo `foto_principal`.
- Como respaldo si una URL falla al cargar, el repo trae la misma imagen en `frontend/public/placeholder-producto.webp`:
  `<img src={p.foto_principal} onError={(e) => (e.currentTarget.src = "/placeholder-producto.webp")} />`

---

## Autenticación (`/auth`)

### `POST /auth/login`
```json
// petición
{"email": "duena@ejemplo.com", "password": "clave-segura"}
// 200
{"access_token": "eyJhbGciOi...", "token_type": "bearer"}
// 401 — mismo mensaje si falla el correo o la contraseña
{"detail": "Credenciales inválidas"}
```

### `POST /auth/recuperar` — "Olvidé mi contraseña" (HU024)
```json
// petición
{"email": "duena@ejemplo.com"}
// 202 — SIEMPRE la misma respuesta, exista o no el correo
{"detail": "Si el correo está registrado, te enviaremos un enlace para restablecer tu contraseña"}
```
El correo (Brevo) lleva un enlace a **`{FRONTEND_URL}/restablecer?token=...`**: el frontend necesita esa ruta.

### `POST /auth/restablecer` — pantalla `/restablecer?token=...`
```json
// petición: el token sale de la URL
{"token": "eyJhbGciOi...", "nueva_contrasena": "nueva-clave-segura"}
// 200
{"detail": "Contraseña actualizada; ya puedes iniciar sesión"}
// 400 — vencido (30 min), ya usado o inválido
{"detail": "El enlace no es válido o ya venció; solicita uno nuevo"}
```
Contraseña: mínimo 8 caracteres (si no, `422`).

### `PUT /auth/contrasena` 🔒 — cambiarla con la sesión iniciada
```json
{"actual": "clave-segura", "nueva": "nueva-clave-segura"}
// 200 {"detail": "Contraseña actualizada"}
// 400 "La contraseña actual no es correcta" | "La nueva contraseña debe ser distinta de la actual"
```

---

## Panel: productos 🔒 (HU014, HU016)

### `GET /admin/categorias`
Para el desplegable del formulario. `[{"id": 1, "nombre": "Boxes y kits", "orden": 1}, ...]` (7 categorías).

### `GET /admin/productos?q=&categoria_id=`
Listado del panel; `q` busca por nombre sin distinguir mayúsculas.
```json
[{"id": 1, "nombre": "Anillo de plata 925 con piedra", "categoria_id": 4, "categoria": "Anillos",
  "precio_base": "40.00", "publicado": true, "num_variantes": 2, "existencias_total": 4,
  "agotado": false, "foto_principal": "https://<ref>.supabase.co/storage/v1/object/public/productos/1/abc.jpg",
  "foto_generica": false}]
```

### `POST /admin/productos` → `201`
```json
{
  "categoria_id": 4,                       // obligatorio
  "nombre": "Anillo de plata 925 con piedra", // obligatorio, máx. 120
  "descripcion": "Anillo de plata 925 con piedra natural facetada.", // obligatorio
  "precio_base": "40.00",                  // obligatorio, > 0
  "material": "Plata 925",                 // opcional, máx. 80
  "medidas": "Piedra de 8 × 10 mm",        // opcional, máx. 80
  "peso_g": "12.50",                       // opcional, > 0
  "es_pieza_natural": true,                // opcional (false)
  "existencias": 3                         // opcional (0): stock de la variante "Única"
}
```
Responde el producto (`publicado: false`, `imagenes: []`). **Todo producto nace con una variante "Única"** que guarda su stock (HU027): si el producto no tiene piedras ni aromas, no hay que hacer nada más.

### `GET /admin/productos/{id}` · `PUT /admin/productos/{id}`
`PUT` recibe los mismos campos que el `POST` salvo `existencias` (el stock se cambia por variante). Ninguno de los dos cambia `publicado`.

### `PATCH /admin/productos/{id}/publicado` — interruptor Activo/Inactivo (HU016)
```json
{"publicado": true}
// 200: el producto actualizado
// 409: {"detail": "No se puede publicar: falta al menos una foto"}  (solo si PUBLICAR_EXIGE_FOTO=true)
```
Despublicar siempre se permite y no borra nada. No existe borrado de productos.
La imagen genérica **no cuenta** como foto: con `PUBLICAR_EXIGE_FOTO=true` hace falta al menos una foto real.

---

## Panel: variantes 🔒 (HU027, HU015)

### `GET /admin/productos/{id}/variantes`
```json
[{"id": 1, "producto_id": 1, "nombre": "Amatista", "precio": "45.00", "precio_efectivo": "45.00",
  "existencias": 3, "agotado": false, "propiedades": "Se le atribuye calma."},
 {"id": 2, "producto_id": 1, "nombre": "Turmalina negra", "precio": null, "precio_efectivo": "40.00",
  "existencias": 2, "agotado": false, "propiedades": null}]
```
`precio: null` = hereda el `precio_base`; muestren siempre `precio_efectivo`.

### `POST /admin/productos/{id}/variantes` → `201` · `PUT /admin/productos/{id}/variantes/{vid}`
```json
{"nombre": "Turmalina negra", "precio": null, "existencias": 2, "propiedades": null}
```
`nombre` obligatorio (máx. 80); `precio` > 0 o `null`; `existencias` ≥ 0.
**Tabla editable (AKASH-46):** la primera piedra se registra **renombrando la variante "Única"** con `PUT`; las demás con `POST`.

### `DELETE /admin/productos/{id}/variantes/{vid}` → `204`
`409` si es la última variante del producto o si ya tiene pedidos (en ese caso, dejen sus existencias en 0).

### `PATCH /admin/variantes/{vid}/stock` — botones +/− del listado (HU015)
```json
{"cambio": -1}          // botones + / −
{"existencias": 12}     // o la cantidad exacta (uno solo de los dos)
// 200, respuesta ligera
{"id": 2, "producto_id": 1, "existencias": 1, "agotado": false}
// 409 {"detail": "Las existencias no pueden quedar en negativo"}
```

---

## Panel: fotos 🔒 (HU014, AKASH-42)

### `POST /admin/productos/{id}/imagenes` → `201`
`multipart/form-data` con **un archivo por petición** en el campo `foto`. JPG, PNG o WEBP, máx. 5 MB, máx. 5 por producto; la primera queda como principal.
```js
const datos = new FormData();
datos.append("foto", archivo);               // <input type="file" accept="image/jpeg,image/png,image/webp">
await fetch(`${API}/admin/productos/${id}/imagenes`, {
  method: "POST", headers: { Authorization: `Bearer ${token}` }, body: datos, // sin Content-Type: lo pone el navegador
});
// 201 {"id": 1, "url": "https://...jpg", "orden": 0, "es_principal": true, "es_referencia_escala": false}
```
Errores: `409` ya tiene 5 · `413` > 5 MB · `415` no es JPG/PNG/WEBP.

### `PATCH /admin/productos/{id}/imagenes/{iid}/principal` → lista de imágenes del producto
### `DELETE /admin/productos/{id}/imagenes/{iid}` → `204` (si era la principal, pasa a serlo la siguiente)

---

## Panel: envíos 🔒 (HU026)

| Ruta | Cuerpo | Nota |
|---|---|---|
| `GET /admin/zonas-envio` | — | `[{"id":1,"nombre":"Lima — motorizado","costo":"10.00","activa":true,"num_distritos":1}]` |
| `POST /admin/zonas-envio` → 201 | `{"nombre":"Lima — motorizado","costo":"10.00","activa":true}` | `costo` ≥ 0 (0 = gratis) |
| `PUT /admin/zonas-envio/{id}` | igual | `activa:false` deja de atender la zona sin borrarla |
| `PUT /admin/zonas-envio/{id}/distritos` | `{"distrito_ids":[1,2,3]}` | mueve esos distritos a la zona |
| `GET /admin/distritos?zona_envio_id=&sin_zona=true` | — | `[{"id":1,"nombre":"Miraflores","zona_envio_id":1,"con_cobertura":true}]` |
| `POST /admin/distritos` → 201 | `{"nombre":"Miraflores","zona_envio_id":1}` | `409` si el nombre ya existe |
| `PUT /admin/distritos/{id}` | igual | `zona_envio_id:null` = sin cobertura |

Ya están cargados los 43 distritos de Lima y 7 del Callao, todos **sin zona** hasta definir costos.

---

## Público: catálogo (sin login)

Solo aparecen productos **publicados**. Nunca se exponen las existencias exactas.

### `GET /catalogo?categoria_id=&q=` — tarjetas
```json
[{"id": 1, "nombre": "Anillo de plata 925 con piedra", "categoria_id": 4, "categoria": "Anillos",
  "precio": "40.00", "precio_desde": true, "disponible": true, "es_pieza_natural": true,
  "foto_principal": "https://...jpg", "foto_generica": false}]
```
- `precio_desde: true` → mostrar **"Desde S/ 40.00"** (HU002).
- `disponible: false` → etiqueta **"Agotado"** y botón de compra deshabilitado (HU003); el producto se sigue mostrando.

### `GET /catalogo/categorias`
Solo las categorías con algún producto publicado, en orden: `[{"id": 4, "nombre": "Anillos"}]`.

### `GET /catalogo/{id}` — ficha
La tarjeta más:
```json
{"descripcion": "...", "material": "Plata 925", "medidas": "Piedra de 8 × 10 mm", "peso_g": null,
 "tiene_variantes": true,
 "variantes": [{"id": 1, "nombre": "Amatista", "precio": "45.00", "disponible": true, "propiedades": "Se le atribuye calma."},
               {"id": 2, "nombre": "Turmalina negra", "precio": "40.00", "disponible": false, "propiedades": null}],
 "imagenes": [{"url": "https://...jpg", "es_principal": true, "es_referencia_escala": false}]}
```
- `tiene_variantes: false` → **no mostrar** el selector (producto con variante "Única").
- Variante con `disponible: false` → opción deshabilitada; las demás siguen activas (HU027).
- Al elegir variante, mostrar su `precio` y sus `propiedades`.
- `es_pieza_natural: true` → mostrar el aviso de variación natural (HU006).
- `404` si no existe o está despublicado.

---

## Público: envío para el checkout (sin login)

### `GET /envio/distritos`
```json
[{"id": 1, "nombre": "Miraflores", "con_cobertura": true, "costo_envio": "10.00"},
 {"id": 2, "nombre": "Ancón", "con_cobertura": false, "costo_envio": null}]
```

### `GET /envio/costo?distrito_id=1`
```json
{"distrito_id": 1, "distrito": "Miraflores", "con_cobertura": true, "costo_envio": "10.00"}
```
`con_cobertura: false` → avisar que no hay envío a ese distrito. El envío a provincia está pendiente de decisión (AKASH-73).
