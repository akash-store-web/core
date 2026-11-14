// Filtros del catálogo público (HU007): categoría, rango de precio y "solo disponibles".
//
// Todo es lógica pura (sin React): recibe datos y devuelve datos. Así se puede probar
// sin abrir el navegador y la página solo se encarga de mostrar.
//
// Los precios se manejan en CÉNTIMOS (enteros): 25.50 → 2550.
// Con decimales, JavaScript falla en cuentas simples (0.1 + 0.2 = 0.30000000000000004);
// con enteros las comparaciones son exactas.

// Nombres de los parámetros en la URL: /catalogo?categoria=pulseras&precio_min=20&precio_max=50&disponibles=1
export const PARAM = {
  categoria: 'categoria',
  precioMin: 'precio_min',
  precioMax: 'precio_max',
  disponibles: 'disponibles',
};

export const PRECIO_MAXIMO_CENTIMOS = 999999; // S/ 9,999.99 (validación de la HU)

// Atajos de precio del panel, pensados para el catálogo actual (precios entre S/ 11 y S/ 89).
export const RANGOS_RAPIDOS = [
  { etiqueta: 'Hasta S/ 25', min: null, max: 2500 },
  { etiqueta: 'S/ 25 a S/ 50', min: 2500, max: 5000 },
  { etiqueta: 'Más de S/ 50', min: 5000, max: null },
];

/* ------------------------------------------------------------------ */
/*  Categorías                                                         */
/* ------------------------------------------------------------------ */

// "Inciensos y limpieza energética" → "inciensos-y-limpieza-energetica"
// La URL queda legible y se puede compartir por WhatsApp.
export function slug(texto) {
  return String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // quita las tildes
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Busca la categoría de la URL. Acepta el slug ("pulseras") o el id ("2").
// Devuelve null si no existe (E7: se ignora y se avisa).
export function buscarCategoria(categorias, valor) {
  if (!valor) return null;
  const buscado = slug(valor);
  return categorias.find((c) => slug(c.nombre) === buscado || String(c.id) === String(valor).trim()) ?? null;
}

/* ------------------------------------------------------------------ */
/*  Precios                                                            */
/* ------------------------------------------------------------------ */

// Monto del backend ("25.00") → céntimos (2500). null si no es un número válido.
export function aCentimos(monto) {
  const numero = Number(monto);
  return Number.isFinite(numero) ? Math.round(numero * 100) : null;
}

// Céntimos → texto para la URL o para un campo: 2500 → "25", 2550 → "25.50"
export function centimosATexto(centimos) {
  if (centimos == null) return '';
  return centimos % 100 === 0 ? String(centimos / 100) : (centimos / 100).toFixed(2);
}

// Valida lo que la clienta escribió en "Mínimo" o "Máximo" (E5).
// Vacío es válido: significa "sin límite" (E6).
// Devuelve { centimos, error }.
export function validarPrecio(texto) {
  let valor = String(texto ?? '').trim().replace(/\s+/g, '').replace(/^s\/\.?/i, ''); // admite "S/ 25"
  if (valor === '') return { centimos: null, error: null };

  if (/^-/.test(valor)) return { centimos: null, error: 'El precio no puede ser negativo.' };

  // "1,500" o "1,500.50" → separador de miles. "25,50" → coma decimal.
  if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(valor)) valor = valor.replace(/,/g, '');
  else valor = valor.replace(',', '.');

  if (!/^\d+(\.\d+)?$/.test(valor)) {
    return { centimos: null, error: 'Escribe solo números, por ejemplo 25 o 25.50.' };
  }

  const [entero, decimales = ''] = valor.split('.');
  if (decimales.length > 2) return { centimos: null, error: 'Usa como máximo 2 decimales.' };

  // Se arma con texto y no con Number(valor) * 100, para no arrastrar errores de redondeo.
  const centimos = Number(entero) * 100 + Number(decimales.padEnd(2, '0'));
  if (centimos > PRECIO_MAXIMO_CENTIMOS) {
    return { centimos: null, error: 'El precio no puede ser mayor a S/ 9,999.99.' };
  }
  return { centimos, error: null };
}

// Valida los dos campos juntos (E4, E5, E6).
// Devuelve { min, max, errores: { min, max, rango }, valido }.
export function validarRango(textoMin, textoMax) {
  const min = validarPrecio(textoMin);
  const max = validarPrecio(textoMax);
  const errores = { min: min.error, max: max.error, rango: null };

  if (!min.error && !max.error && min.centimos != null && max.centimos != null && min.centimos > max.centimos) {
    errores.rango = 'El precio mínimo no puede ser mayor que el máximo.';
  }
  return {
    min: min.centimos,
    max: max.centimos,
    errores,
    valido: !errores.min && !errores.max && !errores.rango,
  };
}

// Rango de precios del producto en céntimos: [más barato, más caro].
// Hoy GET /catalogo solo trae `precio` (el menor). Si el backend agrega `precio_max`
// (el mayor entre las variantes), se usa sin cambiar nada más (E8 completo).
export function rangoDelProducto(producto) {
  const desde = aCentimos(producto.precio);
  const hasta = aCentimos(producto.precio_max ?? producto.precio);
  return [desde, Math.max(desde, hasta ?? desde)];
}

// E8: el producto entra si AL MENOS UNA variante cae en el rango,
// es decir, si su rango [desde, hasta] se cruza con el del filtro.
// Variantes de S/ 40 y S/ 45, filtro hasta S/ 42 → 40 ≤ 42 → entra.
export function cumplePrecio(producto, min, max) {
  const [desde, hasta] = rangoDelProducto(producto);
  if (desde == null) return false;
  return (max == null || desde <= max) && (min == null || hasta >= min);
}

/* ------------------------------------------------------------------ */
/*  URL ⇄ filtros                                                      */
/* ------------------------------------------------------------------ */

// Lee los filtros de la URL y los valida. La URL la puede escribir cualquiera
// (un enlace viejo, un enlace editado a mano), así que nunca se confía en ella.
export function leerFiltros(searchParams, categorias) {
  const valorCategoria = searchParams.get(PARAM.categoria)?.trim() || null;
  const categoria = buscarCategoria(categorias, valorCategoria);

  const textoMin = searchParams.get(PARAM.precioMin) ?? '';
  const textoMax = searchParams.get(PARAM.precioMax) ?? '';
  const rango = validarRango(textoMin, textoMax);

  return {
    categoria, // { id, nombre } o null
    categoriaDesconocida: valorCategoria && !categoria ? valorCategoria : null, // E7
    // Si el precio de la URL no es válido, se ignoran los dos extremos y se avisa.
    precioMin: rango.valido ? rango.min : null,
    precioMax: rango.valido ? rango.max : null,
    precioInvalido: !rango.valido,
    soloDisponibles: searchParams.get(PARAM.disponibles) === '1',
  };
}

// Arma la nueva URL a partir de la actual y los cambios.
// `undefined` = no tocar; `null`, '' o false = quitar el parámetro.
// Conserva los parámetros que no son filtros (por ejemplo ?escenario= del modo simulado).
export function escribirFiltros(searchParams, cambios) {
  const nuevos = new URLSearchParams(searchParams);
  const poner = (clave, valor) => {
    if (valor === undefined) return;
    if (valor === null || valor === '' || valor === false) nuevos.delete(clave);
    else nuevos.set(clave, String(valor));
  };

  if (cambios.categoria !== undefined) poner(PARAM.categoria, cambios.categoria ? slug(cambios.categoria.nombre) : null);
  if (cambios.precioMin !== undefined) poner(PARAM.precioMin, centimosATexto(cambios.precioMin));
  if (cambios.precioMax !== undefined) poner(PARAM.precioMax, centimosATexto(cambios.precioMax));
  if (cambios.soloDisponibles !== undefined) poner(PARAM.disponibles, cambios.soloDisponibles ? '1' : null);
  return nuevos;
}

// Quita todos los filtros (Escenario 3: «Limpiar filtros»), conservando lo demás.
export function limpiarFiltros(searchParams) {
  const nuevos = new URLSearchParams(searchParams);
  Object.values(PARAM).forEach((clave) => nuevos.delete(clave));
  return nuevos;
}

/* ------------------------------------------------------------------ */
/*  Aplicar los filtros a la lista                                     */
/* ------------------------------------------------------------------ */

export function aplicarFiltros(productos, filtros, { sinCategoria = false } = {}) {
  return productos.filter(
    (p) =>
      (sinCategoria || !filtros.categoria || p.categoria_id === filtros.categoria.id) &&
      (!filtros.soloDisponibles || p.disponible) &&
      cumplePrecio(p, filtros.precioMin, filtros.precioMax),
  );
}

// Cuántos productos quedarían en cada categoría con los demás filtros puestos.
// Así la clienta sabe antes de hacer clic si una categoría va a salir vacía.
export function contarPorCategoria(productos, filtros) {
  const conteo = new Map();
  for (const p of aplicarFiltros(productos, filtros, { sinCategoria: true })) {
    conteo.set(p.categoria_id, (conteo.get(p.categoria_id) ?? 0) + 1);
  }
  return conteo;
}

// Si GET /catalogo/categorias falla, las categorías se sacan de los mismos productos.
export function categoriasDeProductos(productos) {
  const vistas = new Map();
  for (const p of productos) {
    if (!vistas.has(p.categoria_id)) vistas.set(p.categoria_id, { id: p.categoria_id, nombre: p.categoria });
  }
  return [...vistas.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
}

// Texto del filtro de precio para chips y avisos (E6: un solo extremo).
export function textoRango(min, max) {
  const s = (c) => `S/ ${centimosATexto(c)}`;
  if (min != null && max != null) return `${s(min)} a ${s(max)}`;
  if (min != null) return `Desde ${s(min)}`;
  if (max != null) return `Hasta ${s(max)}`;
  return '';
}

export function hayFiltros(filtros) {
  return Boolean(filtros.categoria || filtros.precioMin != null || filtros.precioMax != null || filtros.soloDisponibles);
}