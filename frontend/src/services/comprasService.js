import { USE_MOCK } from './config.js';
import { ApiError, apiFetch } from './http.js';
import { sumarStockMock } from './productosService.js';

const esperar = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  DATOS SIMULADOS (solo con VITE_USE_MOCK=true)                      */
/* ------------------------------------------------------------------ */

let siguienteCompraId = 3;

const comprasMock = [
  {
    id: 2,
    fecha: '2026-10-14',
    proveedor: 'Minerales del Sur',
    proveedor_ruc: '20512345678',
    tipo_comprobante: 'factura',
    numero_comprobante: 'F001-000123',
    comprobante: true,
    items: [{ variante_id: 1, producto_id: 1, producto: 'Anillo de plata 925 con piedra', variante: 'Amatista', cantidad: 10, costo_unitario: '12.50' }],
  },
  {
    id: 1,
    fecha: '2026-10-02',
    proveedor: 'Plata Andina',
    proveedor_ruc: null,
    tipo_comprobante: 'boleta',
    numero_comprobante: 'B001-000045',
    comprobante: false,
    items: [{ variante_id: 2, producto_id: 1, producto: 'Anillo de plata 925 con piedra', variante: 'Turmalina negra', cantidad: 4, costo_unitario: '15.00' }],
  },
];

const montoMock = (item) => (Number(item.costo_unitario) * item.cantidad).toFixed(2);

function resumenMock(c) {
  const total = c.items.reduce((suma, i) => suma + Number(i.costo_unitario) * i.cantidad, 0);
  return {
    id: c.id,
    fecha: c.fecha,
    proveedor: c.proveedor,
    tipo_comprobante: c.tipo_comprobante,
    numero_comprobante: c.numero_comprobante,
    total: total.toFixed(2),
    unidades: c.items.reduce((suma, i) => suma + i.cantidad, 0),
    tiene_comprobante: c.comprobante,
  };
}

const detalleMock = (c) => ({
  ...resumenMock(c),
  proveedor_ruc: c.proveedor_ruc,
  comprobante_url: c.comprobante ? 'compras/mock/comprobante.pdf' : null,
  usuario: 'admin@akash.pe',
  items: c.items.map((i) => ({ ...i, subtotal: montoMock(i) })),
});

/* ------------------------------------------------------------------ */
/*  FUNCIONES QUE USA LA INTERFAZ                                      */
/* ------------------------------------------------------------------ */

// Listado: del comprobante más reciente al más antiguo.
export async function listarCompras({ proveedor = '', desde = '', hasta = '' } = {}) {
  if (USE_MOCK) {
    await esperar();
    const texto = proveedor.trim().toLowerCase();
    return comprasMock
      .filter((c) => !texto || c.proveedor.toLowerCase().includes(texto))
      .filter((c) => !desde || c.fecha >= desde)
      .filter((c) => !hasta || c.fecha <= hasta)
      .map(resumenMock);
  }
  const params = new URLSearchParams();
  if (proveedor.trim()) params.set('proveedor', proveedor.trim());
  if (desde) params.set('desde', desde);
  if (hasta) params.set('hasta', hasta);
  const query = params.toString();
  return apiFetch(`/admin/compras${query ? `?${query}` : ''}`);
}

export async function obtenerCompra(compraId) {
  if (USE_MOCK) {
    await esperar(250);
    const compra = comprasMock.find((c) => c.id === compraId);
    if (!compra) throw new ApiError('Compra no encontrada', 404);
    return detalleMock(compra);
  }
  return apiFetch(`/admin/compras/${compraId}`);
}

/*
  HU033 escenarios 1, 3 y 5. Guarda la compra y suma el stock en una sola operación.
  `datos` = { proveedor, proveedor_ruc, tipo_comprobante, numero_comprobante, fecha,
              items: [{ variante_id, cantidad, costo_unitario }] }
  409 si ese comprobante de ese proveedor ya existe.
*/
export async function registrarCompra(datos) {
  if (USE_MOCK) {
    await esperar(600);
    const repetida = comprasMock.some(
      (c) =>
        c.proveedor.toLowerCase() === datos.proveedor.toLowerCase() &&
        c.tipo_comprobante === datos.tipo_comprobante &&
        c.numero_comprobante.toUpperCase() === datos.numero_comprobante.toUpperCase(),
    );
    if (repetida) {
      throw new ApiError(
        'Ese comprobante de ese proveedor ya está registrado; no se volvió a sumar el stock',
        409,
        'duplicado',
      );
    }
    const items = datos.items.map((i) => {
      const info = sumarStockMock(i.variante_id, i.cantidad);
      if (!info) throw new ApiError(`No existen las variantes: [${i.variante_id}]`, 422);
      return { variante_id: i.variante_id, ...info, cantidad: i.cantidad, costo_unitario: i.costo_unitario };
    });
    const compra = {
      id: siguienteCompraId++,
      fecha: datos.fecha,
      proveedor: datos.proveedor,
      proveedor_ruc: datos.proveedor_ruc,
      tipo_comprobante: datos.tipo_comprobante,
      numero_comprobante: datos.numero_comprobante.toUpperCase(),
      comprobante: false,
      items,
    };
    comprasMock.unshift(compra);
    return detalleMock(compra);
  }
  return apiFetch('/admin/compras', { method: 'POST', body: datos });
}

// HU033 escenario 2: foto o PDF (máx. 5 MB) en el campo «archivo». Si ya había uno, lo reemplaza.
export async function subirComprobante(compraId, archivo) {
  if (USE_MOCK) {
    await esperar(500);
    const compra = comprasMock.find((c) => c.id === compraId);
    if (!compra) throw new ApiError('Compra no encontrada', 404);
    compra.comprobante = true;
    return detalleMock(compra);
  }
  const formData = new FormData();
  formData.append('archivo', archivo);
  return apiFetch(`/admin/compras/${compraId}/comprobante`, { method: 'POST', formData });
}

// El bucket es privado: se pide un enlace que vence a los 5 minutos justo antes de abrirlo.
export async function enlaceComprobante(compraId) {
  if (USE_MOCK) {
    await esperar(300);
    return { url: '/placeholder-producto.webp', expira_en_segundos: 300 };
  }
  return apiFetch(`/admin/compras/${compraId}/comprobante`);
}