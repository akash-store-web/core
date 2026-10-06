from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers.admin_productos import router as admin_productos_router
from app.routers.auth import router as auth_router

app = FastAPI(title="Akash Store API")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(admin_productos_router)

@app.get("/health")
def health():
    return {"status": "ok"}
