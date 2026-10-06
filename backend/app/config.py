import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# HU016: exigir al menos una foto para publicar. Activar cuando exista la subida de fotos (HU014 #4).
PUBLICAR_EXIGE_FOTO = os.getenv("PUBLICAR_EXIGE_FOTO", "false").strip().lower() == "true"
# HU024: base del enlace de recuperación de contraseña (pantalla /restablecer del frontend).
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
# HU014 (AKASH-42): fotos de productos en Supabase Storage.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "productos")
# HU024: correo con Brevo (API HTTP). CORREO_REMITENTE debe estar verificado en Brevo (Senders).
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
CORREO_REMITENTE = os.getenv("CORREO_REMITENTE", "")
CORREO_REMITENTE_NOMBRE = os.getenv("CORREO_REMITENTE_NOMBRE", "Akash Store")
# Imagen genérica para productos sin foto real: foto_principal nunca llega vacía al frontend.
# No cuenta como foto para PUBLICAR_EXIGE_FOTO. Está subida en el bucket (placeholders/producto.webp).
FOTO_GENERICA_URL = os.getenv("FOTO_GENERICA_URL") or (
    f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/placeholders/producto.webp"
    if SUPABASE_URL else "/placeholder-producto.webp"
)
