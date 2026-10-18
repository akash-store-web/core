"""HU033: compras de mercadería con comprobante (el stock entra solo por aquí o por ajustes con motivo)."""
from datetime import date

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models.usuario import Usuario
from app.schemas.compra import CompraIn, CompraOut, CompraResumen, IngresoPorCompra
from app.services import comprobantes, compras as servicio

router = APIRouter(prefix="/admin", tags=["admin: compras"], dependencies=[Depends(get_current_admin)])


@router.post("/compras", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
def registrar_compra(datos: CompraIn, usuario: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Guarda la compra y suma el stock de cada variante en una sola transacción.
    409 si ese comprobante del mismo proveedor ya existe (no se duplica el ingreso)."""
    return servicio.registrar_compra(db, datos, usuario.id)


@router.get("/compras", response_model=list[CompraResumen])
def listar_compras(proveedor: str | None = None, desde: date | None = None, hasta: date | None = None,
                   db: Session = Depends(get_db)):
    """Del comprobante más reciente al más antiguo; filtros opcionales por proveedor y rango de fechas."""
    return servicio.listar_compras(db, proveedor, desde, hasta)


@router.get("/compras/{compra_id}", response_model=CompraOut)
def obtener_compra(compra_id: int, db: Session = Depends(get_db)):
    return servicio.obtener_compra(db, compra_id)


@router.get("/productos/{producto_id}/compras", response_model=list[IngresoPorCompra])
def compras_de_producto(producto_id: int, db: Session = Depends(get_db)):
    """HU033 escenario 4: con qué compras ingresó el stock de este producto (fecha, comprobante y cantidad)."""
    return servicio.compras_de_producto(db, producto_id)


@router.post("/compras/{compra_id}/comprobante", response_model=CompraOut)
def subir_comprobante(compra_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """AKASH-115: adjunta la foto o el PDF del comprobante (maximo 5 MB) al bucket privado."""
    comprobantes.adjuntar_comprobante(db, compra_id, archivo.file.read())
    return servicio.obtener_compra(db, compra_id)


@router.get("/compras/{compra_id}/comprobante")
def ver_comprobante(compra_id: int, db: Session = Depends(get_db)):
    """Enlace temporal (5 minutos) para abrir el comprobante; el bucket no es publico."""
    return comprobantes.enlace_comprobante(db, compra_id)