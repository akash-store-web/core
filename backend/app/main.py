from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers.admin_envios import router as admin_envios_router
from app.routers.admin_imagenes import router as admin_imagenes_router
from app.routers.admin_productos import router as admin_productos_router
from app.routers.admin_variantes import router as admin_variantes_router
from app.routers.admin_variantes import stock_router as admin_stock_router
from app.routers.auth import router as auth_router
from app.routers.carrito import router as carrito_router
from app.routers.catalogo import router as catalogo_router
from app.routers.envio import router as envio_router

app = FastAPI(title="Akash Store API")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(admin_productos_router)
app.include_router(admin_variantes_router)
app.include_router(admin_stock_router)
app.include_router(admin_imagenes_router)
app.include_router(admin_envios_router)
app.include_router(envio_router)
app.include_router(catalogo_router)
app.include_router(carrito_router)

@app.get("/health")
def health():
    return {"status": "ok"}
