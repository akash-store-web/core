/*
  Lógica pura de la bandeja de pedidos del panel (HU017), sin React: se puede probar en Node.
*/

// Estados del filtro, en el orden de la HU (el backend acepta exactamente estos valores).
export const ESTADOS_PEDIDO = [
  { valor: 'pendiente', etiqueta: 'Pendiente' },
  { valor: 'confirmado', etiqueta: 'Confirmado' },
  { valor: 'enviado', etiqueta: 'Enviado' },
  { valor: 'entregado', etiqueta: 'Entregado' },
  { valor: 'cancelado', etiqueta: 'Cancelado' },
];

export const POR_PAGINA = 20; // E7

export const esEstadoValido = (valor) => ESTADOS_PEDIDO.some((e) => e.valor === valor);
export const etiquetaEstado = (valor) => ESTADOS_PEDIDO.find((e) => e.valor === valor)?.etiqueta ?? valor;

/*
  Los filtros viven en la URL (/adminPanel/pedidos?estado=pendiente&q=P-0012&pagina=2):
  así el botón Atrás funciona y la propietaria puede volver a la bandeja tal como la dejó.
  Lo que no es válido se ignora y se avisa (nunca rompe la página).
*/
export function leerFiltrosPedidos(params) {
  const avisos = [];

  let estado = params.get('estado') || null;
  if (estado && !esEstadoValido(estado)) {
    avisos.push(`El estado «${estado}» no existe; se muestran todos los pedidos.`);
    estado = null;
  }

  const q = (params.get('q') ?? '').trim().slice(0, 50);

  const textoPagina = params.get('pagina');
  const pagina = /^\d{1,4}$/.test(textoPagina ?? '') && Number(textoPagina) > 0 ? Number(textoPagina) : 1;

  return { estado, q, pagina, avisos };
}

// E7: corta la lista en páginas de 20. Si la página pedida no existe, se usa la última.
export function paginar(lista, pagina, porPagina = POR_PAGINA) {
  const total = lista.length;
  const totalPaginas = Math.max(1, Math.ceil(total / porPagina));
  const actual = Math.min(Math.max(1, pagina), totalPaginas);
  const inicio = (actual - 1) * porPagina;
  return {
    items: lista.slice(inicio, inicio + porPagina),
    pagina: actual,
    totalPaginas,
    total,
    desde: total === 0 ? 0 : inicio + 1,
    hasta: Math.min(inicio + porPagina, total),
  };
}

// Fecha y hora en Lima, sin importar la zona horaria de la computadora: "21/11/2026, 14:05".
const formatoFecha = new Intl.DateTimeFormat('es-PE', {
  timeZone: 'America/Lima',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

export function fechaHoraLima(iso) {
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? '—' : formatoFecha.format(fecha);
}

// Celular de 9 dígitos que empieza con 9 → enlace al chat de la clienta con un saludo ya escrito.
// Devuelve null si el número guardado no es válido (el botón no se muestra).
export function enlaceChatClienta({ telefono, nombre, numero }) {
  const celular = String(telefono ?? '').replace(/\D/g, '').replace(/^51(?=9\d{8}$)/, '');
  if (!/^9\d{8}$/.test(celular)) return null;
  const primerNombre = String(nombre ?? '').trim().split(/\s+/)[0];
  const mensaje = `Hola${primerNombre ? ` ${primerNombre}` : ''}, te escribo de Akash Store Perú por tu pedido ${numero}.`;
  return `https://wa.me/51${celular}?text=${encodeURIComponent(mensaje)}`;
}

// El backend guarda "Única" en los productos sin variantes: no aporta nada en pantalla.
export const nombreVariante = (variante) => (variante && variante !== 'Única' ? variante : null);
