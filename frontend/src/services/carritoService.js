import { USE_MOCK } from './config.js';
import { ApiError } from './http.js';
import { buscarVarianteMock, pedirPublico } from './catalogoService.js';
import { MAX_LINEAS, MAX_POR_LINEA, normalizarCarrito, validarCantidad } from '../utils/carrito.js';

// El carrito vive en el navegador (HU009, Esc. 4): sobrevive a cerrar la pestaña en el mismo
// dispositivo. El servidor solo valida cada ítem contra el stock y el precio reales (E10).

const CLAVE = 'akash_carrito';
const EVENTO = 'carrito:actualizado';

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  Lectura y guardado en el navegador                                 */
/*  obtenerCarrito + suscribirCarrito forman una "tienda externa" que  */
/*  React lee con useSyncExternalStore (ver CarritoProvider).          */
/* ------------------------------------------------------------------ */

// useSyncExternalStore exige que, si nada cambió, se devuelva EL MISMO arreglo.
// Por eso se guarda el último texto leído y su lista ya normalizada.
let textoEnCache;
let itemsEnCache = [];

// localStorage puede fallar (modo privado, almacenamiento lleno): nunca rompe la página.
function leerTexto() {
  try {
    return localStorage.getItem(CLAVE);
  } catch {
    return null;
  }
}

export function obtenerCarrito() {
  const texto = leerTexto();
  if (texto !== textoEnCache) {
    textoEnCache = texto;
    let datos;
    try {
      datos = JSON.parse(texto ?? '[]');
    } catch {
      datos = []; // E10: JSON roto o manipulado → carrito vacío, sin romper la página
    }
    itemsEnCache = normalizarCarrito(datos);
  }
  return itemsEnCache;
}

// Se mantiene el nombre anterior para no romper a quien ya lo use.
export const leerCarrito = obtenerCarrito;

// Avisa a React cuando el carrito cambia en esta pestaña (EVENTO) o en otra ('storage').
export function suscribirCarrito(avisar) {
  const alCambiarEnOtraPestana = (evento) => {
    if (evento.key === CLAVE || evento.key === null) avisar();
  };
  window.addEventListener(EVENTO, avisar);
  window.addEventListener('storage', alCambiarEnOtraPestana);
  return () => {
    window.removeEventListener(EVENTO, avisar);
    window.removeEventListener('storage', alCambiarEnOtraPestana);
  };
}

function guardarCarrito(items) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(normalizarCarrito(items)));
  } catch {
    throw new ApiError('No se pudo guardar el carrito en este navegador.', 0);
  }
  window.dispatchEvent(new Event(EVENTO));
}

/* ------------------------------------------------------------------ */
/*  Validación contra el servidor: POST /carrito/validar               */
/* ------------------------------------------------------------------ */

/*
  Escenarios del mock (agregar a la URL de cualquier página):
    ?escenario=seagota       → todo lo que se valida aparece agotado (HU028 E7 / HU009 E8)
    ?escenario=despublicado  → la variante 2 (Cuarzo rosa) ya no está publicada (E8)
    ?escenario=preciocambio  → todos los precios subieron S/ 5.00 (E9)
  Stock simulado: 2 unidades del Cuarzo rosa (id 2, para el Esc. 3) y 3 del resto.
*/
const stockMock = (varianteId) => (varianteId === 2 ? 2 : 3);

async function validarMock(items) {
  const escenario = new URLSearchParams(window.location.search).get('escenario');
  await esperar(500);

  // Igual que el backend: la misma variante en varias líneas se suma.
  const pedidas = new Map();
  for (const { variante_id, cantidad, precio_visto } of items) {
    const previa = pedidas.get(variante_id);
    pedidas.set(variante_id, {
      cantidad: (previa?.cantidad ?? 0) + cantidad,
      precio_visto: previa?.precio_visto ?? precio_visto ?? null,
    });
  }

  const resultado = [...pedidas].map(([variante_id, { cantidad, precio_visto }]) => {
    const encontrado = buscarVarianteMock(variante_id);
    if (!encontrado || (escenario === 'despublicado' && variante_id === 2)) {
      return {
        variante_id, producto_id: encontrado?.ficha.id ?? null, producto: encontrado?.ficha.nombre ?? null,
        variante: encontrado?.variante.nombre ?? null, es_pieza_natural: false, cantidad,
        estado: 'no_disponible', cantidad_maxima: 0, precio_unitario: null, subtotal: '0.00',
        mensaje: 'Este producto ya no está disponible; quítalo del pedido',
        precio_anterior: null, precio_cambio: false,
      };
    }
    const { ficha, variante } = encontrado;
    const precio = (Number(variante.precio) + (escenario === 'preciocambio' ? 5 : 0)).toFixed(2);
    const stock = escenario === 'seagota' || !variante.disponible ? 0 : stockMock(variante_id);
    let maximo = stock;
    let estado = 'ok';
    let mensaje = null;
    if (stock === 0) {
      estado = 'agotado';
      mensaje = 'Agotado; quítalo del pedido';
    } else if (cantidad > MAX_POR_LINEA) {
      maximo = Math.min(MAX_POR_LINEA, stock);
      estado = 'limite';
      mensaje = 'Máximo 10 unidades por producto; para más, escríbenos por WhatsApp';
    } else if (cantidad > stock) {
      estado = 'stock_insuficiente';
      mensaje = `Solo quedan ${stock}; ajusta la cantidad`;
    }
    const precioCambio = precio_visto != null && Number(precio_visto) !== Number(precio);
    if (precioCambio && !mensaje) {
      mensaje = `El precio cambió de S/ ${Number(precio_visto).toFixed(2)} a S/ ${precio}`;
    }
    return {
      variante_id, producto_id: ficha.id, producto: ficha.nombre, variante: variante.nombre,
      es_pieza_natural: ficha.es_pieza_natural, cantidad, estado, cantidad_maxima: maximo,
      precio_unitario: precio, subtotal: (Number(precio) * Math.min(cantidad, maximo)).toFixed(2),
      mensaje, precio_anterior: precioCambio ? Number(precio_visto).toFixed(2) : null,
      precio_cambio: precioCambio,
    };
  });

  return {
    valido: resultado.every((i) => i.estado === 'ok'),
    items: resultado,
    total: resultado.reduce((suma, i) => suma + Number(i.subtotal), 0).toFixed(2),
    aviso_pieza_natural: null,
  };
}

// items: [{ variante_id, cantidad, precio? }]. El precio guardado viaja como `precio_visto`
// solo para que el servidor avise si cambió (E9); nunca se usa para calcular (E10).
export async function validarCarrito(items, { signal } = {}) {
  if (items.length === 0) return { valido: false, items: [], total: '0.00', aviso_pieza_natural: null };

  const cuerpo = items.map(({ variante_id, cantidad, precio }) => ({
    variante_id,
    cantidad,
    ...(precio != null ? { precio_visto: precio } : {}),
  }));
  if (USE_MOCK) return validarMock(cuerpo);
  return pedirPublico('/carrito/validar', { signal, method: 'POST', body: { items: cuerpo } });
}

/* ------------------------------------------------------------------ */
/*  FUNCIONES QUE USA LA INTERFAZ                                       */
/* ------------------------------------------------------------------ */

// Desde la ficha: vuelve a consultar la disponibilidad y, solo si el servidor la confirma, agrega
// (HU028 E7). Si la variante ya estaba en el carrito, se suma en la misma línea (HU009 E7).
// Devuelve:
//   { ok: true, item, precioAnterior }               → agregado (precioAnterior si el precio cambió)
//   { ok: false, estado, cantidadMaxima, enCarrito }  → no se agregó
//      estado: 'agotado' | 'no_disponible' | 'stock_insuficiente' | 'limite' | 'lineas'
// Lanza ApiError si no se pudo consultar (sin red, servidor caído).
export async function agregarAlCarrito({ ficha, variante, cantidad = 1 }) {
  const carrito = obtenerCarrito();
  const existente = carrito.find((i) => i.variante_id === variante.id);
  const enCarrito = existente?.cantidad ?? 0;
  const cantidadTotal = enCarrito + cantidad;

  // E6: máximo 10 por variante (se revisa antes de ir al servidor)
  if (cantidadTotal > MAX_POR_LINEA) {
    return { ok: false, estado: 'limite', cantidadMaxima: MAX_POR_LINEA - enCarrito, enCarrito };
  }
  if (!existente && carrito.length >= MAX_LINEAS) {
    return { ok: false, estado: 'lineas', cantidadMaxima: 0, enCarrito };
  }

  const respuesta = await validarCarrito([
    { variante_id: variante.id, cantidad: cantidadTotal, precio: variante.precio },
  ]);
  const resultado = respuesta?.items?.find((i) => i.variante_id === variante.id);
  if (!resultado) throw new ApiError('Respuesta inesperada al validar el carrito.', 0);

  // La variante debe pertenecer a este producto (validación de la HU028; E8 lo rechaza el backend)
  if (resultado.estado === 'ok' && resultado.producto_id !== ficha.id) {
    return { ok: false, estado: 'no_disponible', cantidadMaxima: 0, enCarrito };
  }
  if (resultado.estado !== 'ok') {
    return { ok: false, estado: resultado.estado, cantidadMaxima: resultado.cantidad_maxima, enCarrito };
  }

  const precio = resultado.precio_unitario ?? variante.precio;
  const item = {
    variante_id: variante.id,
    producto_id: ficha.id,
    producto: ficha.nombre,
    // HU028 E4: el pedido debe mostrar la variante elegida. «Única» no se muestra.
    variante: ficha.tiene_variantes ? variante.nombre : null,
    precio,
    foto: ficha.foto_principal,
    cantidad: cantidadTotal,
  };

  // Se vuelve a leer: el carrito pudo cambiar mientras se esperaba al servidor.
  const actual = obtenerCarrito();
  guardarCarrito(
    actual.some((i) => i.variante_id === variante.id)
      ? actual.map((i) => (i.variante_id === variante.id ? item : i))
      : [...actual, item],
  );

  return {
    ok: true,
    item,
    precioAnterior: Number(precio) !== Number(variante.precio) ? variante.precio : null,
  };
}

// Desde el carrito (Esc. 2 / Esc. 3).
// - Bajar la cantidad no necesita al servidor: se guarda al momento.
// - Subirla se confirma antes con el servidor; si no alcanza, NO se cambia.
// Devuelve { ok: true, resultado? } o { ok: false, estado, cantidadMaxima, resultado? }.
// `resultado` es el ítem que respondió el servidor (para actualizar la revisión en pantalla).
export async function cambiarCantidad(varianteId, nueva) {
  const validacion = validarCantidad(nueva);
  if (!validacion.ok) return { ok: false, estado: validacion.tipo, cantidadMaxima: null };

  const item = obtenerCarrito().find((i) => i.variante_id === varianteId);
  if (!item) return { ok: false, estado: 'no_disponible', cantidadMaxima: 0 };

  const cantidad = validacion.valor;
  if (cantidad <= item.cantidad) {
    guardarCarrito(obtenerCarrito().map((i) => (i.variante_id === varianteId ? { ...i, cantidad } : i)));
    return { ok: true };
  }

  const respuesta = await validarCarrito([{ ...item, cantidad }]);
  const resultado = respuesta?.items?.find((i) => i.variante_id === varianteId);
  if (!resultado) throw new ApiError('Respuesta inesperada al validar el carrito.', 0);
  if (resultado.estado !== 'ok') {
    return { ok: false, estado: resultado.estado, cantidadMaxima: resultado.cantidad_maxima, resultado };
  }

  guardarCarrito(
    obtenerCarrito().map((i) =>
      i.variante_id === varianteId
        ? { ...i, cantidad, precio: resultado.precio_unitario ?? i.precio }
        : i,
    ),
  );
  return { ok: true, resultado };
}

// Esc. 2: eliminar una línea.
export function quitarDelCarrito(varianteId) {
  guardarCarrito(obtenerCarrito().filter((i) => i.variante_id !== varianteId));
}

// E9: después de validar, el precio guardado pasa a ser el vigente (así el aviso no se repite
// en la próxima apertura). Las cantidades NO se tocan: las decide la clienta.
export function aplicarRevision(respuesta) {
  const porVariante = new Map((respuesta?.items ?? []).map((i) => [i.variante_id, i]));
  let huboCambios = false;

  const actualizados = obtenerCarrito().map((item) => {
    const servidor = porVariante.get(item.variante_id);
    if (servidor?.precio_unitario == null) return item;
    const precio = Number(servidor.precio_unitario).toFixed(2);
    const producto = servidor.producto ?? item.producto;
    if (precio === item.precio && producto === item.producto) return item;
    huboCambios = true;
    return { ...item, precio, producto };
  });

  if (huboCambios) guardarCarrito(actualizados);
}
