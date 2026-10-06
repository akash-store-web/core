# Akash Store — Plataforma de catálogo y venta en línea

Catálogo web y panel de administración para **Akash Store Perú**, una tienda de cuarzos y productos holísticos que opera desde 2019 por Instagram y WhatsApp.

El negocio es real y el producto se le entrega a la propietaria al terminar el proyecto.

---

## El problema que resuelve

Hoy cada venta exige una conversación manual completa con la propietaria: informar el precio, ir a su casa a revisar si hay stock, mandar fotos, coordinar el pago y la entrega. En una venta documentada, la clienta esperó **1 hora y 52 minutos** la primera respuesta y se necesitaron más de setenta mensajes para vender S/ 45. El catálogo actual, un PDF de Canva, le pide al cliente "consultar stock" porque no puede informar disponibilidad.

La plataforma permite que la clienta vea precio y disponibilidad y compre sola, y que la propietaria administre productos y pedidos desde el celular.

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React |
| Backend | FastAPI (Python) |
| Base de datos | PostgreSQL en Supabase |
| Almacenamiento de imágenes | Supabase Storage |
| Autenticación | JWT emitido por el backend |
| Despliegue frontend | Vercel |
| Despliegue backend | Render |
| Pruebas | pytest |
| Diseño | Figma |
| Gestión | Jira (proyecto `AKASH`) |

> El stack está definido pero aún no congelado. Cualquier cambio se acuerda en equipo y se refleja aquí y en el informe.

---

## Estructura

```
akash-store-web/
├── backend/            # API FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── models/     # Modelos de la base de datos
│   │   ├── routers/    # Endpoints por módulo
│   │   ├── schemas/    # Validación con Pydantic
│   │   └── services/   # Lógica de negocio
│   ├── tests/          # pytest
│   └── requirements.txt
├── frontend/           # Aplicación React
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/   # Llamadas a la API
│   └── package.json
├── docs/               # Diagrama ER, wireframes, guía de estilos
├── CONTRIBUTING.md     # Cómo trabajamos — léelo antes de tu primer commit
└── README.md
```

---

## Levantar el proyecto en local

**Requisitos:** Python 3.11 o superior, Node 20 o superior, Git.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completa los valores (ver más abajo)
uvicorn app.main:app --reload
```

API en `http://localhost:8000`. Documentación automática en `http://localhost:8000/docs`.

Scripts del backend (desde `backend/`, con el `.env` apuntando a Supabase). Los de carga simulan por defecto y solo escriben con `--aplicar`:

| Script | Para qué |
|---|---|
| `python -m scripts.crear_propietaria` | Crea la cuenta del panel (pide email y contraseña) |
| `python -m scripts.restablecer_contrasena` | Plan de emergencia si la propietaria pierde el acceso |
| `python -m scripts.seed_distritos` | Carga los 43 distritos de Lima y 7 del Callao, sin zona |
| `python -m scripts.seed_productos` | Carga productos de ejemplo, despublicados y sin fotos |
| `python -m scripts.generar_postman` | Regenera `docs/postman/` y falla si alguna ruta de la API no está en la colección |

Ningún script crea ni modifica tablas: el esquema se administra en Supabase.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Aplicación en `http://localhost:5173`.

---

## Variables de entorno

**Nunca** subas un archivo `.env` al repositorio. Solo se versiona `.env.example`, con los nombres de las variables y sin valores.

Las credenciales reales están en el gestor de contraseñas compartido del equipo. Si no tienes acceso, pídeselo al Product Owner.

### backend/.env

```
DATABASE_URL=              # Supabase → Connect → Session pooler (Render no llega a la conexión directa IPv6)
SUPABASE_URL=              # https://<ref>.supabase.co
SUPABASE_SECRET_KEY=       # llave secreta (sb_secret_...); solo la usa el backend para Storage
SUPABASE_BUCKET=productos  # bucket público de fotos de producto
JWT_SECRET=                # cadena aleatoria larga: python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:5173          # en Render: también la URL de Vercel, separadas por coma
PUBLICAR_EXIGE_FOTO=false  # true = no se puede publicar un producto sin al menos una foto (HU016)
FRONTEND_URL=http://localhost:5173          # base del enlace de recuperación de contraseña (HU024)
FOTO_GENERICA_URL=         # opcional: por defecto, placeholders/producto.webp del bucket (productos sin foto)
BREVO_API_KEY=             # API de Brevo para el correo de recuperación; vacía = el enlace va al log
CORREO_REMITENTE=          # remitente verificado en Brevo (Senders)
CORREO_REMITENTE_NOMBRE=Akash Store
```

Render gratuito bloquea los puertos SMTP: por eso el correo se envía por la API HTTP de Brevo.
Las pruebas (`pytest`) usan SQLite en memoria y nunca tocan Supabase, Storage ni Brevo.

### frontend/.env

```
VITE_API_URL=http://localhost:8000
VITE_WHATSAPP_NUMBER=      # número de la tienda, sin + ni espacios
```

---

## Equipo

| Integrante | Rol | Foco técnico |
|---|---|---|
| Correa Reyes, Raúl Benjamín | Developer | Backend y base de datos |
| Cruces Contreras, Fiorella | Scrum Master | QA |
| Quiroz Luna, Jeremies Ronaldo | Developer | Frontend |
| Cervantes Galvan, Litzy Shannon | Developer | Full stack, UX/UI e integración |
| López Maya, Diego Arturo | Product Owner · Integrador | Apoyo en base de datos y migraciones |

---

## Calendario

| Sprint | Del | Al | Entrega en ISIL+ |
|---|---|---|---|
| 1 | 22 set | 12 oct | Avance 2 — lunes 12 de octubre, 23:59 |
| 2 | 13 oct | 2 nov | Avance 3 — lunes 2 de noviembre, 23:59 |
| 3 | 3 nov | 23 nov | Avance 4 — lunes 23 de noviembre, 23:59 |
| 4 | 24 nov | 14 dic | Proyecto Final — lunes 14 de diciembre, 23:59 |

Sprints de tres semanas. La Sprint Review con la propietaria se hace dos o tres días antes de cada cierre, y su feedback entra al backlog antes de la exposición.

**Sprint 1:** entorno desplegado, registro de productos con variantes y catálogo público visible con el catálogo real cargado.
**Sprint 2:** ficha de producto completa y carrito.
**Sprint 3:** checkout, pago y gestión de pedidos. Con esto el MVP queda completo.
**Sprint 4:** pruebas de aceptación con la propietaria, documentación, respaldos y entrega.

---

## Enlaces

- **Backlog en Jira:** proyecto `AKASH`
- **Diseño en Figma:** [completar]
- **Catálogo público desplegado:** [completar]
- **Panel de administración:** [completar]

---

## Reglas que no se negocian

1. **Ninguna credencial entra al repositorio.** Ni contraseñas, ni cadenas de conexión, ni llaves de API, ni "temporalmente". Borrar un secreto del historial de Git es un dolor de cabeza; evitarlo cuesta cero.
2. **Nadie sube directo a `main`.** Todo entra por pull request con revisión de otro integrante.
3. **Ningún dato personal de clientas reales** en el repositorio, en capturas ni en datos de prueba.

---

## Contexto académico

Proyecto Tecnológico, ISIL, periodo 2026-2, NRC 3710. Dieciséis semanas, cinco sprints, marco Scrum.

El producto funcionando es el entregable principal; la documentación lo acompaña pero no lo sustituye.
