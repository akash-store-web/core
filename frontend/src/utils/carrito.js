/*
  Lógica pura del carrito (HU009), sin React ni localStorage: se puede probar en Node.

  Regla de oro (E10): lo guardado en el navegador es solo una referencia. Precios y
  disponibilidad los decide siempre el servidor (POST /carrito/validar).
*/

export const MAX_POR_LINEA = 10; // E6: para más unidades, la clienta escribe por WhatsApp
export const MAX_LINEAS = 50; // el backend acepta hasta 50 líneas por carrito

// HU006 E4: el mismo texto por defecto que el backend (AVISO_PIEZA_NATURAL_DEFECTO en config.py).
// Solo se usa si el servidor no manda uno; lo normal es mostrar el texto que viene del servidor.
export const AVISO_PIEZA_NATURAL_DEFECTO =
  'Cada pieza es natural y única: la que recibas puede variar en forma, tamaño y tono respecto de la fotografía.';
const AVISO_MAXIMO = 300;

// Estados del servidor que sacan la línea del total y no dejan continuar (E8)
const FUERA_DEL_TOTAL = ['agotado', 'no_disponible'];
// Estados en los que solo se puede comprar una parte (Esc. 3 / E6)
const CANTIDAD_LIMITADA = ['stock_insuficiente', 'limite'];

/* ------------------------------------------------------------------ */
/*  E5 / E6: validar la cantidad que escribe la clienta                */
/* ------------------------------------------------------------------ */

// Devuelve { ok: true, valor } o { ok: false, tipo, error }.
// tipo: 'vacio' | 'formato' | 'cero' | 'limite'
export function validarCantidad(texto) {
  const limpio = String(texto ?? '').trim();

  if (limpio === '') return { ok: false, tipo: 'vacio', error: 'Escribe una cantidad.' };
  if (/^-/.test(limpio)) {
    return { ok: false, tipo: 'formato', error: 'La cantidad no puede ser negativa.' };
  }
  if (/^\d+[.,]\d*$/.test(limpio)) {
    return { ok: false, tipo: 'formato', error: 'Escribe un número entero, sin decimales.' };
  }
  if (!/^\d+$/.test(limpio)) {
    return { ok: false, tipo: 'formato', error: 'Escribe solo números.' };
  }

  const valor = Number(limpio);
  if (valor === 0) {
    return {
      ok: false,
      tipo: 'cero',
      error: 'La cantidad mínima es 1. Si ya no lo quieres, usa «Eliminar».',
    };
  }
  if (valor > MAX_POR_LINEA) {
    return { ok: false, tipo: 'limite', error: `Puedes llevar hasta ${MAX_POR_LINEA} unidades por producto.` };
  }
  return { ok: true, valor };
}

/* ------------------------------------------------------------------ */
/*  E7 / E10: limpiar lo que viene del navegador                       */
/* ------------------------------------------------------------------ */

const esIdPositivo = (valor) => Number.isInteger(valor) && valor > 0;

function cantidadSegura(valor) {
  const numero = Number(valor);
  if (!Number.isInteger(numero) || numero < 1) return 1;
  return Math.min(numero, MAX_POR_LINEA);
}

function precioSeguro(valor) {
  const numero = Number(valor);
  return valor != null && Number.isFinite(numero) && numero >= 0 ? numero.toFixed(2) : null;
}

// Convierte cualquier cosa (lo leído de localStorage, quizá manipulado) en una lista válida:
// - descarta lo que no tenga un variante_id entero positivo,
// - deja la cantidad entre 1 y 10 (el backend responde 422 desde 11 y tumbaría todo el carrito),
// - junta en una sola línea la misma variante repetida (E7),
// - el precio queda solo como referencia (puede ser null).
export function normalizarCarrito(datos) {
  if (!Array.isArray(datos)) return [];

  const porVariante = new Map();
  for (const crudo of datos) {
    if (crudo == null || typeof crudo !== 'object' || !esIdPositivo(crudo.variante_id)) continue;

    const previo = porVariante.get(crudo.variante_id);
    if (previo) {
      previo.cantidad = Math.min(previo.cantidad + cantidadSegura(crudo.cantidad), MAX_POR_LINEA);
      continue;
    }
    porVariante.set(crudo.variante_id, {
      variante_id: crudo.variante_id,
      producto_id: esIdPositivo(crudo.producto_id) ? crudo.producto_id : null,
      producto: typeof crudo.producto === 'string' && crudo.producto.trim() ? crudo.producto : 'Producto',
      variante: typeof crudo.variante === 'string' && crudo.variante.trim() ? crudo.variante : null,
      precio: precioSeguro(crudo.precio),
      foto: typeof crudo.foto === 'string' && crudo.foto ? crudo.foto : null,
      cantidad: cantidadSegura(crudo.cantidad),
    });
  }
  return [...porVariante.values()].slice(0, MAX_LINEAS);
}

/* ------------------------------------------------------------------ */
/*  Montos: siempre en céntimos (enteros) para no sumar decimales      */
/* ------------------------------------------------------------------ */

// 0.1 + 0.2 = 0.30000000000000004 en JavaScript; 10 + 20 = 30 céntimos, siempre exacto.
export function aCentimos(monto) {
  const numero = Number(monto);
  return monto != null && Number.isFinite(numero) ? Math.round(numero * 100) : 0;
}

export const contarUnidades = (items) => items.reduce((suma, item) => suma + item.cantidad, 0);

/* ------------------------------------------------------------------ */
/*  Juntar lo guardado con lo que respondió el servidor                */
/* ------------------------------------------------------------------ */

// items: lo guardado (ya normalizado). revision: { [variante_id]: ítem de POST /carrito/validar }.
// Una línea sin revisión queda 'pendiente' (aún no se confirmó con el servidor).
export function combinarConRevision(items, revision = {}) {
  return items.map((item) => {
    const servidor = revision[item.variante_id];
    const estado = servidor?.estado ?? 'pendiente';
    const cantidadMaxima = servidor?.cantidad_maxima ?? null;
    const precio = servidor?.precio_unitario ?? item.precio;

    const cuenta = !FUERA_DEL_TOTAL.includes(estado);
    // Como el backend: si no alcanza el stock, el subtotal usa lo que sí se puede comprar.
    const unidadesCobradas = !cuenta
      ? 0
      : CANTIDAD_LIMITADA.includes(estado) && cantidadMaxima != null
        ? Math.min(item.cantidad, cantidadMaxima)
        : item.cantidad;

    return {
      ...item,
      precio,
      estado,
      cantidadMaxima,
      cuenta,
      esPiezaNatural: Boolean(servidor?.es_pieza_natural), // HU006: lo dice el servidor, no el navegador
      precioCambio: Boolean(servidor?.precio_cambio),
      precioAnterior: servidor?.precio_anterior ?? null,
      subtotalCentimos: aCentimos(precio) * unidadesCobradas,
    };
  });
}

// Resumen del carrito para el pie del panel.
export function resumirCarrito(lineas) {
  return {
    totalCentimos: lineas.reduce((suma, l) => suma + l.subtotalCentimos, 0),
    noDisponibles: lineas.filter((l) => FUERA_DEL_TOTAL.includes(l.estado)).length,
    porAjustar: lineas.filter((l) => CANTIDAD_LIMITADA.includes(l.estado)).length,
    preciosCambiados: lineas.filter((l) => l.precioCambio).length,
    // Se puede intentar continuar si no hay nada marcado como bloqueante.
    // ('pendiente' no bloquea: al pulsar «Continuar» se vuelve a validar todo.)
    puedeContinuar:
      lineas.length > 0 &&
      lineas.every((l) => !FUERA_DEL_TOTAL.includes(l.estado) && !CANTIDAD_LIMITADA.includes(l.estado)),
  };
}

// Cuando la clienta BAJA la cantidad no hace falta preguntar al servidor: si queda dentro de
// lo que el servidor ya dijo que hay, la línea pasa a estar bien.
export function revisionTrasBajar(servidor, nuevaCantidad) {
  if (!servidor) return servidor;
  const alcanza =
    CANTIDAD_LIMITADA.includes(servidor.estado) && nuevaCantidad <= servidor.cantidad_maxima;
  return {
    ...servidor,
    cantidad: nuevaCantidad,
    ...(alcanza ? { estado: 'ok', mensaje: null } : {}),
  };
}

/*
  HU006 Esc. 2 / E5 / E6: aviso de pieza natural para el carrito y el pedido.
  - Una sola vez, con los productos a los que aplica (sin repetir el nombre si hay varias piedras).
  - La lista sale de las líneas ACTUALES: si la clienta quita la pieza, el aviso deja de nombrarla
    sin esperar otra validación. Las líneas agotadas o retiradas no cuentan (no se van a comprar).
  - Si el servidor dejó de marcar el producto como natural (E5), su línea ya no trae la marca.
  Devuelve { texto, productos } o null si no aplica.
*/
export function avisoPiezaNatural(lineas, textoServidor) {
  const productos = [...new Set(lineas.filter((l) => l.esPiezaNatural && l.cuenta).map((l) => l.producto))];
  if (productos.length === 0) return null;

  const texto = String(textoServidor ?? '').trim();
  return {
    texto: texto && texto.length <= AVISO_MAXIMO ? texto : AVISO_PIEZA_NATURAL_DEFECTO,
    productos,
  };
}
