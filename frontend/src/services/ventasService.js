import { USE_MOCK } from './config.js';
import { ApiError, apiFetch } from './http.js';

const esperar = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

const NOMBRES_MES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

// "octubre de 2026"
export const nombreMes = (anio, mes) => `${NOMBRES_MES[mes - 1]} de ${anio}`;

/* ------------------------------------------------------------------ */
/*  DATOS SIMULADOS (solo con VITE_USE_MOCK=true)                      */
/*  Septiembre no tiene ventas a propósito, para ver el mensaje.       */
/* ------------------------------------------------------------------ */

const ventasMock = {
  '2026-10': { pedidos: 3, productos: 175, envio: 35 },
  '2026-11': { pedidos: 5, productos: 420, envio: 50 },
};

function resumenMock(anio, mes) {
  const d = ventasMock[`${anio}-${String(mes).padStart(2, '0')}`] ?? { pedidos: 0, productos: 0, envio: 0 };
  return {
    anio,
    mes,
    pedidos: d.pedidos,
    total_productos: d.productos.toFixed(2),
    total_envio: d.envio.toFixed(2),
    total: (d.productos + d.envio).toFixed(2),
  };
}

/* ------------------------------------------------------------------ */
/*  PANEL (HU019): GET /admin/ventas/mes                               */
/*  Sin parámetros devuelve el mes actual. anio y mes van juntos.      */
/* ------------------------------------------------------------------ */

export async function obtenerVentasMes(anio, mes) {
  if (USE_MOCK) {
    await esperar();
    const hoy = new Date();
    const anioActual = hoy.getFullYear();
    const mesActual = hoy.getMonth() + 1;
    const a = anio ?? anioActual;
    const m = mes ?? mesActual;
    if (m < 1 || m > 12) throw new ApiError('El mes debe estar entre 1 y 12', 422);
    if (a * 12 + m > anioActual * 12 + mesActual) throw new ApiError('No se puede consultar un mes futuro', 422);
    if (a * 12 + m < 2026 * 12 + 9) throw new ApiError('No hay registros antes de septiembre de 2026', 422);

    const actual = resumenMock(a, m);
    const sinVentas = actual.pedidos === 0;
    const esPrimerMes = a === 2026 && m === 9;
    return {
      ...actual,
      sin_ventas: sinVentas,
      mensaje: sinVentas ? `No hubo ventas confirmadas en ${nombreMes(a, m)}` : null,
      mes_anterior: esPrimerMes ? null : m === 1 ? resumenMock(a - 1, 12) : resumenMock(a, m - 1),
    };
  }
  const consulta = anio == null || mes == null ? '' : `?anio=${anio}&mes=${mes}`;
  return apiFetch(`/admin/ventas/mes${consulta}`);
}
