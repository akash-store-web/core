import { API_URL, USE_MOCK } from './config.js';
import { ApiError } from './http.js';

// Catálogo PÚBLICO (lo ve la clienta, sin sesión).
// No usa apiFetch a propósito: apiFetch envía el token del panel y, ante un 401,
// cierra la sesión y manda a /admin. Nada de eso tiene sentido en la tienda.

export const PLACEHOLDER = '/placeholder-producto.webp';

// Render (plan gratuito) puede tardar ~50 s en despertar. Pasado este tiempo
// se corta la espera y se muestra el mensaje con "Reintentar".
const TIEMPO_MAXIMO_MS = 75000;

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  DATOS SIMULADOS (solo con VITE_USE_MOCK=true)                      */
/*  Para probar escenarios agrega a la URL:                            */
/*    ?escenario=vacio   → catálogo vacío                               */
/*    ?escenario=error   → servidor no disponible                       */
/*    ?escenario=lento   → carga lenta (12 s)                           */
/*    ?escenario=seagota → al agregar al carrito, la variante ya se     */
/*                         agotó (HU028, E7)                            */
/*  Las fotos simuladas usan la imagen genérica; el "?foto=N" solo      */
/*  las diferencia entre sí para poder probar la galería.               */
/* ------------------------------------------------------------------ */

const foto = (n, extra = {}) => ({
  url: `${PLACEHOLDER}?foto=${n}`,
  es_principal: false,
  es_referencia_escala: false,
  ...extra,
});

const fichasMock = [
  {
    id: 1, nombre: 'Anillo de plata 925 con piedra', categoria_id: 4, categoria: 'Anillos',
    precio: '40.00', precio_desde: true, disponible: true, es_pieza_natural: false,
    foto_generica: false,
    descripcion: 'Anillo artesanal de plata 925 con una piedra natural engastada a mano. Elige la piedra que más resuene contigo.',
    material: 'Plata 925', medidas: 'Talla ajustable (6 a 9)', peso_g: '4.20',
    tiene_variantes: true,
    variantes: [
      { id: 1, nombre: 'Amatista', precio: '45.00', disponible: true, propiedades: 'Se le atribuye calma, intuición y claridad mental.' },
      { id: 2, nombre: 'Cuarzo rosa', precio: '40.00', disponible: true, propiedades: 'Se le atribuye amor propio y armonía en los vínculos.' },
      { id: 3, nombre: 'Turmalina negra', precio: '40.00', disponible: false, propiedades: 'Se le atribuye protección y enraizamiento.' },
    ],
    imagenes: [
      foto(1, { es_principal: true }),
      foto(2),
      foto(3, { es_referencia_escala: true }),
    ],
  },
  {
    // Sin fotos: el backend devuelve la imagen genérica (AKASH-74)
    id: 3, nombre: 'Spray áurico', categoria_id: 1, categoria: 'Boxes y kits',
    precio: '25.00', precio_desde: false, disponible: true, es_pieza_natural: false,
    foto_generica: true,
    descripcion: 'Spray con aceites esenciales para limpiar la energía de tus espacios.',
    material: null, medidas: '100 ml', peso_g: null,
    tiene_variantes: false,
    variantes: [{ id: 5, nombre: 'Única', precio: '25.00', disponible: true, propiedades: null }],
    imagenes: [],
  },
  {
    // Nombre muy largo + agotado
    id: 4,
    nombre: 'Box de limpieza energética con cuarzos, palo santo, salvia blanca y vela de soya aromática',
    categoria_id: 1, categoria: 'Boxes y kits',
    precio: '89.00', precio_desde: false, disponible: false, es_pieza_natural: false,
    foto_generica: false,
    descripcion: 'Box con pulsera de cuarzo, spray áurico, vela, inciensos con tabla y sales de baño.',
    material: null, medidas: null, peso_g: null,
    tiene_variantes: false,
    variantes: [{ id: 6, nombre: 'Única', precio: '89.00', disponible: false, propiedades: null }],
    imagenes: [foto(4, { es_principal: true }), foto(5)],
  },
  {
    // La foto no carga → debe verse la imagen genérica
    id: 5, nombre: 'Drusa de amatista', categoria_id: 5, categoria: 'Cuarzos en bruto',
    precio: '120.00', precio_desde: false, disponible: true, es_pieza_natural: true,
    foto_generica: false,
    descripcion: 'Drusa de amatista en bruto, ideal para tu altar o escritorio.',
    material: 'Amatista natural', medidas: '8 × 6 cm aprox.', peso_g: '350.00',
    tiene_variantes: false,
    variantes: [{ id: 7, nombre: 'Única', precio: '120.00', disponible: true, propiedades: 'Se le atribuye calma y protección del espacio.' }],
    imagenes: [{ url: '/foto-que-no-existe.webp', es_principal: true, es_referencia_escala: false }],
  },
  {
    // Sin precio: NUNCA se lista ni tiene ficha pública (HU016)
    id: 6, nombre: 'Producto sin precio (no debe verse)', categoria_id: 7, categoria: 'Inciensos',
    precio: '0.00', precio_desde: false, disponible: true, es_pieza_natural: false,
    foto_generica: true, descripcion: '', material: null, medidas: null, peso_g: null,
    tiene_variantes: false, variantes: [], imagenes: [],
  },
  {
    // Kit con aromas a elegir (origen de la HU028)
    id: 7, nombre: 'Kit de inciensos naturales', categoria_id: 7, categoria: 'Inciensos',
    precio: '12.50', precio_desde: false, disponible: true, es_pieza_natural: false,
    foto_generica: false,
    descripcion: 'Caja de 20 varitas de incienso natural. Elige el aroma que prefieras dentro de los disponibles.',
    material: null, medidas: '20 varitas', peso_g: null,
    tiene_variantes: true,
    variantes: [
      { id: 8, nombre: 'Sándalo', precio: '12.50', disponible: true, propiedades: 'Aroma cálido, se usa para meditar.' },
      { id: 9, nombre: 'Lavanda', precio: '12.50', disponible: true, propiedades: 'Aroma suave, se usa para relajarse.' },
      { id: 10, nombre: 'Palo santo', precio: '12.50', disponible: false, propiedades: 'Aroma amaderado, se usa para limpiar espacios.' },
    ],
    imagenes: [foto(6, { es_principal: true }), foto(7)],
  },
  {
    // Todas las variantes agotadas (HU028, E9)
    id: 8, nombre: 'Pulsera de cuarzo', categoria_id: 2, categoria: 'Pulseras',
    precio: '45.00', precio_desde: false, disponible: false, es_pieza_natural: false,
    foto_generica: false,
    descripcion: 'Pulsera elástica de cuentas de cuarzo de 8 mm.',
    material: 'Cuarzo natural', medidas: 'Elástica, talla única', peso_g: null,
    tiene_variantes: true,
    variantes: [
      { id: 11, nombre: 'Cuarzo rosa', precio: '45.00', disponible: false, propiedades: 'Se le atribuye amor propio.' },
      { id: 12, nombre: 'Pirita', precio: '45.00', disponible: false, propiedades: 'Se le atribuye abundancia.' },
    ],
    imagenes: [foto(8, { es_principal: true })],
  },
];

// La ficha simulada se arma igual que la del backend (foto_principal incluida).
function aFicha(f) {
  const principal = f.imagenes.find((i) => i.es_principal) ?? f.imagenes[0];
  return { ...f, foto_principal: principal ? principal.url : PLACEHOLDER };
}

// La tarjeta del catálogo es un resumen de la ficha (ProductoCatalogo del backend).
function aTarjeta(f) {
  const { id, nombre, categoria_id, categoria, precio, precio_desde, disponible,
    es_pieza_natural, foto_principal, foto_generica } = aFicha(f);
  return { id, nombre, categoria_id, categoria, precio, precio_desde, disponible,
    es_pieza_natural, foto_principal, foto_generica };
}

// Solo para el mock de carritoService: busca una variante y su producto.
export function buscarVarianteMock(varianteId) {
  for (const ficha of fichasMock) {
    const variante = ficha.variantes.find((v) => v.id === varianteId);
    if (variante) return { ficha, variante };
  }
  return null;
}

async function simularRed() {
  const escenario = new URLSearchParams(window.location.search).get('escenario');
  await esperar(escenario === 'lento' ? 12000 : 600);
  if (escenario === 'error') throw new ApiError('Error simulado', 503);
  return escenario;
}

/* ------------------------------------------------------------------ */
/*  Petición pública (sin token) con límite de tiempo y cancelación    */
/* ------------------------------------------------------------------ */

// También la usa carritoService (POST /carrito/validar).
export async function pedirPublico(path, { signal, method = 'GET', body } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIEMPO_MAXIMO_MS);
  const cancelarDesdeFuera = () => controller.abort();
  signal?.addEventListener('abort', cancelarDesdeFuera);

  const opciones = { method, signal: controller.signal };
  if (body !== undefined) {
    opciones.headers = { 'Content-Type': 'application/json' };
    opciones.body = JSON.stringify(body);
  }

  try {
    let response;
    try {
      response = await fetch(`${API_URL}${path}`, opciones);
    } catch {
      throw new ApiError('No se pudo conectar con el servidor.', 0);
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(`${path} respondió ${response.status}.`, response.status, data?.detail);
    }
    return data;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancelarDesdeFuera);
  }
}

/* ------------------------------------------------------------------ */
/*  Validación de respaldo                                             */
/*  El backend ya filtra publicado = true y precio > 0; aquí se vuelve */
/*  a comprobar lo que la vista puede comprobar, por si acaso.          */
/* ------------------------------------------------------------------ */

function esListable(producto) {
  return (
    producto != null &&
    Number.isInteger(producto.id) &&
    typeof producto.nombre === 'string' &&
    producto.nombre.trim() !== '' &&
    Number(producto.precio) > 0
  );
}

// Hoy GET /catalogo devuelve un arreglo. Si más adelante se pagina
// ({ items: [...] }), esta función ya lo soporta.
function normalizarLista(data) {
  const lista = Array.isArray(data) ? data : data?.items;
  if (!Array.isArray(lista)) throw new ApiError('Respuesta inesperada del catálogo.', 0);
  return lista.filter(esListable);
}

// El id de la URL debe ser un entero positivo (validación de la HU028).
export function esIdValido(id) {
  return /^\d{1,9}$/.test(String(id)) && Number(id) > 0;
}

// Error que la ficha muestra como «este producto ya no está disponible».
const noDisponible = () => new ApiError('Producto no encontrado', 404);

/* ------------------------------------------------------------------ */
/*  FUNCIONES QUE USA LA INTERFAZ                                      */
/* ------------------------------------------------------------------ */

// `signal` permite cancelar la petición (por ejemplo, si la clienta sale de la página).
export async function listarCatalogo({ signal } = {}) {
  if (USE_MOCK) {
    const escenario = await simularRed();
    if (escenario === 'vacio') return [];
    return normalizarLista(fichasMock.map(aTarjeta));
  }
  return normalizarLista(await pedirPublico('/catalogo', { signal }));
}

// Ficha pública de un producto (HU028).
// Lanza ApiError con status 404 si el id no es válido, no existe o está despublicado.
export async function obtenerFicha(id, { signal } = {}) {
  if (!esIdValido(id)) throw noDisponible(); // ni siquiera se consulta al servidor

  let ficha;
  if (USE_MOCK) {
    await simularRed();
    const encontrada = fichasMock.find((f) => f.id === Number(id));
    ficha = encontrada ? aFicha(encontrada) : null;
  } else {
    try {
      ficha = await pedirPublico(`/catalogo/${id}`, { signal });
    } catch (error) {
      // 404: no existe o fue despublicado. 422: id que el backend no acepta.
      if (error.status === 404 || error.status === 422) throw noDisponible();
      throw error;
    }
  }

  if (!esListable(ficha)) throw noDisponible();
  return {
    ...ficha,
    imagenes: Array.isArray(ficha.imagenes) ? ficha.imagenes : [],
    variantes: Array.isArray(ficha.variantes) ? ficha.variantes : [],
  };
}