import { USE_MOCK } from './config.js';
import { ApiError } from './http.js';
import { pedirPublico } from './catalogoService.js';
import { validarCarrito } from './carritoService.js';
import { listarDistritosEnvio } from './envioService.js';

// Pedido público (HU010): la clienta, sin cuenta, registra su pedido y lo envía por WhatsApp.
// El servidor pone precios, envío y total (E7) y evita el doble registro (E9).

const CLAVE_ULTIMO = 'akash_ultimo_pedido';
const VIGENCIA_ULTIMO_MS = 7 * 24 * 60 * 60 * 1000; // el aviso del último pedido se muestra 7 días

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  MOCK (VITE_USE_MOCK=true): imita POST /pedidos                     */
/*    ?escenario=agotaalenviar → el carrito se ve bien, pero al enviar  */
/*                         el primer producto se agotó (409, E6)      */
/*    ?escenario=error   → servidor no disponible                       */
/* ------------------------------------------------------------------ */

let ultimoNumeroMock = 0;
const recientesMock = []; // para simular el doble envío (E9)

async function registrarMock(cuerpo) {
  const escenario = new URLSearchParams(window.location.search).get('escenario');
  await esperar(900);
  if (escenario === 'error') throw new ApiError('Error simulado', 503);

  const distrito = (await listarDistritosEnvio()).find((d) => d.id === cuerpo.distrito_id);
  if (!distrito) throw new ApiError('/pedidos respondió 422.', 422, 'Elige un distrito de la lista');
  if (cuerpo.modalidad_entrega === 'delivery' && !distrito.con_cobertura) {
    throw new ApiError('/pedidos respondió 422.', 422,
      'El distrito no tiene cobertura de envío; escríbenos por WhatsApp para coordinar');
  }

  const firma = `${cuerpo.celular}|${cuerpo.items.map((i) => `${i.variante_id}:${i.cantidad}`).sort().join(',')}`;
  const repetido = recientesMock.find((r) => r.firma === firma && Date.now() - r.cuando < 2 * 60 * 1000);
  if (repetido) return { ...repetido.pedido, repetido: true };

  // Mismas reglas de stock que el carrito (el mock de validarCarrito ya entiende ?escenario=seagota)
  const revision = await validarCarrito(cuerpo.items);
  if (escenario === 'agotaalenviar') {
    Object.assign(revision.items[0], { estado: 'agotado', cantidad_maxima: 0, mensaje: 'Agotado; quítalo del pedido' });
    revision.valido = false;
  }
  if (!revision.valido) {
    throw new ApiError('/pedidos respondió 409.', 409, {
      mensaje: 'Algunos productos ya no están disponibles; quítalos o ajusta la cantidad antes de enviar',
      items: revision.items
        .filter((i) => i.estado !== 'ok')
        .map(({ variante_id, producto, variante, estado, cantidad_maxima, mensaje }) =>
          ({ variante_id, producto, variante, estado, cantidad_maxima, mensaje })),
    });
  }

  const subtotal = revision.items.reduce((suma, i) => suma + Number(i.subtotal), 0);
  const envio = cuerpo.modalidad_entrega === 'delivery' ? Number(distrito.costo_envio) : 0;
  ultimoNumeroMock += 1;
  const pedido = {
    numero: `P-${String(ultimoNumeroMock).padStart(4, '0')}`,
    estado: 'pendiente',
    fecha: new Date().toISOString(),
    nombre: cuerpo.nombre,
    celular: cuerpo.celular,
    distrito: distrito.nombre,
    modalidad_entrega: cuerpo.modalidad_entrega,
    direccion: cuerpo.direccion,
    referencia: cuerpo.referencia,
    items: revision.items.map((i) => ({
      variante_id: i.variante_id,
      producto: i.producto,
      variante: i.variante,
      cantidad: i.cantidad,
      precio_unitario: i.precio_unitario,
      subtotal: i.subtotal,
    })),
    subtotal: subtotal.toFixed(2),
    costo_envio: envio.toFixed(2),
    total: (subtotal + envio).toFixed(2),
    repetido: false,
  };
  recientesMock.push({ firma, cuando: Date.now(), pedido });
  return pedido;
}

/* ------------------------------------------------------------------ */
/*  FUNCIONES QUE USA LA INTERFAZ                                       */
/* ------------------------------------------------------------------ */

// cuerpo: armarCuerpoPedido(...) de utils/pedido.js.
// Devuelve el pedido registrado (201) o el ya registrado con `repetido: true` (200, E9).
// Lanza ApiError: 409 con detail { mensaje, items } (E6) · 422 con detail (texto o lista) · 0 sin conexión.
export async function registrarPedido(cuerpo) {
  if (USE_MOCK) return registrarMock(cuerpo);
  return pedirPublico('/pedidos', { method: 'POST', body: cuerpo });
}

/* ------------------------------------------------------------------ */
/*  Último pedido (Esc. 3 y E8): sobrevive a recargar o volver luego   */
/* ------------------------------------------------------------------ */

// Se guarda solo lo necesario para la confirmación: número, resumen y el enlace de WhatsApp.
export function guardarUltimoPedido(pedido, enlace) {
  try {
    localStorage.setItem(CLAVE_ULTIMO, JSON.stringify({ pedido, enlace, guardado: Date.now() }));
  } catch {
    // Sin localStorage la confirmación igual se ve en pantalla; solo no sobrevive a recargar.
  }
}

// Devuelve { pedido, enlace } o null (si no hay, está dañado o tiene más de 7 días).
export function leerUltimoPedido() {
  try {
    const datos = JSON.parse(localStorage.getItem(CLAVE_ULTIMO) ?? 'null');
    const valido =
      datos &&
      typeof datos.pedido?.numero === 'string' &&
      typeof datos.enlace === 'string' &&
      datos.enlace.startsWith('https://wa.me/') && // E10 de HU009: nunca abrir un enlace manipulado
      Date.now() - datos.guardado < VIGENCIA_ULTIMO_MS;
    return valido ? { pedido: datos.pedido, enlace: datos.enlace } : null;
  } catch {
    return null;
  }
}

export function olvidarUltimoPedido() {
  try {
    localStorage.removeItem(CLAVE_ULTIMO);
  } catch {
    // nada que hacer
  }
}
