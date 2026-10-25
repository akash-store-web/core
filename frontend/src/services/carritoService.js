import { USE_MOCK } from './config.js';
import { ApiError } from './http.js';
import { buscarVarianteMock, pedirPublico } from './catalogoService.js';

// El carrito vive en el navegador (así lo define el backend para HU009);
// el servidor solo valida cada ítem contra el stock y el precio reales.
// Aquí solo está lo que necesita la HU028: validar y agregar una variante.
// La pantalla del carrito llegará con su propia historia.

const CLAVE = 'akash_carrito';
const STOCK_MOCK = 3; // unidades simuladas de cada variante disponible

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  Lectura y guardado en el navegador                                 */
/* ------------------------------------------------------------------ */

// localStorage puede fallar (modo privado, almacenamiento lleno): nunca rompe la página.
export function leerCarrito() {
  try {
    const datos = JSON.parse(localStorage.getItem(CLAVE) ?? '[]');
    return Array.isArray(datos) ? datos : [];
  } catch {
    return [];
  }
}

function guardarCarrito(items) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(items));
  } catch {
    throw new ApiError('No se pudo guardar el carrito en este navegador.', 0);
  }
  // Aviso para quien lo necesite (por ejemplo, el contador del carrito en la cabecera).
  window.dispatchEvent(new Event('carrito:actualizado'));
}

/* ------------------------------------------------------------------ */
/*  Validación contra el servidor: POST /carrito/validar               */
/* ------------------------------------------------------------------ */

async function validarMock(items) {
  const escenario = new URLSearchParams(window.location.search).get('escenario');
  await esperar(500);

  const resultado = items.map(({ variante_id, cantidad }) => {
    const encontrado = buscarVarianteMock(variante_id);
    if (!encontrado) {
      return {
        variante_id, producto_id: null, producto: null, variante: null, es_pieza_natural: false,
        cantidad, estado: 'no_disponible', cantidad_maxima: 0, precio_unitario: null,
        subtotal: '0.00', mensaje: 'Este producto ya no está disponible.',
      };
    }
    const { ficha, variante } = encontrado;
    const stock = escenario === 'seagota' || !variante.disponible ? 0 : STOCK_MOCK;
    let estado = 'ok';
    if (stock === 0) estado = 'agotado';
    else if (cantidad > stock) estado = 'stock_insuficiente';
    return {
      variante_id, producto_id: ficha.id, producto: ficha.nombre, variante: variante.nombre,
      es_pieza_natural: ficha.es_pieza_natural, cantidad, estado, cantidad_maxima: stock,
      precio_unitario: variante.precio,
      subtotal: (Number(variante.precio) * cantidad).toFixed(2), mensaje: null,
    };
  });

  return {
    valido: resultado.every((i) => i.estado === 'ok'),
    items: resultado,
    total: resultado.reduce((suma, i) => suma + Number(i.subtotal), 0).toFixed(2),
  };
}

// items: [{ variante_id, cantidad }]
export async function validarCarrito(items, { signal } = {}) {
  if (USE_MOCK) return validarMock(items);
  return pedirPublico('/carrito/validar', { signal, method: 'POST', body: { items } });
}

/* ------------------------------------------------------------------ */
/*  FUNCIÓN QUE USA LA FICHA                                            */
/* ------------------------------------------------------------------ */

// Vuelve a consultar la disponibilidad y, solo si el servidor la confirma, agrega (HU028, E7).
// Devuelve:
//   { ok: true, item, precioAnterior }       → agregado (precioAnterior si el precio cambió)
//   { ok: false, estado, cantidadMaxima, enCarrito }  → no se agregó
// Lanza ApiError si no se pudo consultar (sin red, servidor caído).
export async function agregarAlCarrito({ ficha, variante, cantidad = 1 }) {
  const carrito = leerCarrito();
  const existente = carrito.find((i) => i.variante_id === variante.id);
  const enCarrito = existente?.cantidad ?? 0;
  const cantidadTotal = enCarrito + cantidad;

  const respuesta = await validarCarrito([{ variante_id: variante.id, cantidad: cantidadTotal }]);
  const resultado = respuesta?.items?.find((i) => i.variante_id === variante.id);
  if (!resultado) throw new ApiError('Respuesta inesperada al validar el carrito.', 0);

  // La variante debe pertenecer a este producto (validación de la HU; E8 lo rechaza el backend)
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
    // E4: el pedido debe mostrar la variante elegida. «Única» no se muestra.
    variante: ficha.tiene_variantes ? variante.nombre : null,
    precio,
    foto: ficha.foto_principal,
    cantidad: cantidadTotal,
  };

  guardarCarrito(
    existente
      ? carrito.map((i) => (i.variante_id === variante.id ? item : i))
      : [...carrito, item],
  );

  return {
    ok: true,
    item,
    precioAnterior: Number(precio) !== Number(variante.precio) ? variante.precio : null,
  };
}