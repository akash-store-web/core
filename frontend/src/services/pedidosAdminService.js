import { USE_MOCK } from './config.js';
import { ApiError, apiFetch } from './http.js';

// Pedidos en el PANEL (HU017). Usa apiFetch: envía el token y, ante un 401, cierra la sesión (E6).

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  MOCK (VITE_USE_MOCK=true): 26 pedidos ficticios para probar la     */
/*  paginación (E7). En la URL de la bandeja:                          */
/*    ?escenario=vacio → sin pedidos (E4) · ?escenario=error → falla   */
/* ------------------------------------------------------------------ */

const PRODUCTOS_MOCK = [
  { variante_id: 1, producto_id: 1, producto: 'Anillo de plata 925 con piedra', variante: 'Amatista', precio: 45 },
  { variante_id: 2, producto_id: 1, producto: 'Anillo de plata 925 con piedra', variante: 'Cuarzo rosa', precio: 40 },
  { variante_id: 5, producto_id: 3, producto: 'Spray áurico', variante: 'Única', precio: 25 },
  { variante_id: 13, producto_id: 9, producto: 'Collar de cuarzo cristal', variante: 'Única', precio: 35 },
  { variante_id: 8, producto_id: 7, producto: 'Kit de inciensos naturales', variante: 'Sándalo', precio: 12.5 },
];
const NOMBRES_MOCK = ['Ana Prueba', 'Lucía Ficticia', 'María Ejemplo', 'Rosa Demo', 'Carmen Prueba', 'Sofía Ficticia'];
const ESTADOS_MOCK = ['pendiente', 'pendiente', 'confirmado', 'enviado', 'entregado', 'cancelado', 'pendiente'];

function crearPedidosMock() {
  const ahora = Date.now();
  return Array.from({ length: 26 }, (_, i) => {
    const id = 26 - i; // el más reciente primero, como el backend
    const items = PRODUCTOS_MOCK.filter((_, j) => (i + j) % 3 === 0).slice(0, 3).map((p, j) => ({
      variante_id: p.variante_id, producto_id: p.producto_id, producto: p.producto, variante: p.variante,
      cantidad: (j % 2) + 1, precio_unitario: p.precio.toFixed(2), subtotal: (p.precio * ((j % 2) + 1)).toFixed(2),
    }));
    const subtotal = items.reduce((s, it) => s + Number(it.subtotal), 0);
    const delivery = i % 3 !== 2;
    const envio = delivery ? 10 : 0;
    const fecha = new Date(ahora - i * 7 * 60 * 60 * 1000).toISOString();
    const estado = ESTADOS_MOCK[i % ESTADOS_MOCK.length];
    const nombre = NOMBRES_MOCK[i % NOMBRES_MOCK.length];
    return {
      id,
      numero: `P-${String(id).padStart(4, '0')}`,
      fecha,
      estado,
      clienta: {
        nombre,
        telefono: `9${String(11111111 + id * 1013).slice(0, 8)}`,
        correo: null,
        direccion: delivery ? `Calle Ficticia ${100 + id}` : null,
        referencia: delivery && i % 2 === 0 ? 'Frente al parque' : null,
      },
      distrito: ['Miraflores', 'San Isidro', 'Barranco'][i % 3],
      modalidad_entrega: delivery ? 'delivery' : 'recojo',
      items,
      subtotal: subtotal.toFixed(2),
      costo_envio: envio.toFixed(2),
      total: (subtotal + envio).toFixed(2),
      metodo_pago: 'whatsapp',
      historial: [
        { estado: 'pendiente', fecha, usuario: null },
        ...(estado !== 'pendiente' ? [{ estado, fecha: new Date(Date.parse(fecha) + 3600000).toISOString(), usuario: 'propietaria@ejemplo.com' }] : []),
      ],
    };
  });
}

let pedidosMock = null;
const obtenerMock = () => (pedidosMock ??= crearPedidosMock());

async function simular() {
  const escenario = new URLSearchParams(window.location.search).get('escenario');
  await esperar(escenario === 'lento' ? 8000 : 500);
  if (escenario === 'error') throw new ApiError('Error simulado', 503);
  return escenario;
}

const aBandeja = (p) => ({
  id: p.id, numero: p.numero, fecha: p.fecha, clienta: p.clienta.nombre, telefono: p.clienta.telefono,
  total: p.total, metodo_pago: p.metodo_pago, estado: p.estado,
  num_items: p.items.reduce((s, it) => s + it.cantidad, 0),
});

/* ------------------------------------------------------------------ */
/*  FUNCIONES QUE USA EL PANEL                                          */
/* ------------------------------------------------------------------ */

// GET /admin/pedidos?estado=&q= → del más reciente al más antiguo.
// `q` busca por número, nombre o celular (lo hace el backend).
export async function listarPedidosAdmin({ estado, q } = {}) {
  if (USE_MOCK) {
    const escenario = await simular();
    if (escenario === 'vacio') return [];
    const texto = (q ?? '').trim().toLowerCase();
    return obtenerMock()
      .filter((p) => !estado || p.estado === estado)
      .filter((p) => !texto || [p.numero, p.clienta.nombre, p.clienta.telefono].some((v) => v.toLowerCase().includes(texto)))
      .map(aBandeja);
  }
  const params = new URLSearchParams();
  if (estado) params.set('estado', estado);
  if (q) params.set('q', q);
  const consulta = params.toString();
  return apiFetch(`/admin/pedidos${consulta ? `?${consulta}` : ''}`);
}

// GET /admin/pedidos/{id}. Lanza ApiError 404 si no existe (E6).
export async function obtenerPedidoAdmin(id) {
  if (USE_MOCK) {
    await simular();
    const pedido = obtenerMock().find((p) => p.id === Number(id));
    if (!pedido) throw new ApiError('Pedido no encontrado', 404);
    return structuredClone(pedido);
  }
  return apiFetch(`/admin/pedidos/${id}`);
}

// Para el contador de la barra lateral: cuántos pedidos esperan atención.
export async function contarPedidosPendientes() {
  const pendientes = await listarPedidosAdmin({ estado: 'pendiente' });
  return Array.isArray(pendientes) ? pendientes.length : 0;
}
