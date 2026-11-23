/*
  Lógica pura del pedido por WhatsApp (HU010 + AKASH-196), sin React: se puede probar en Node.
  Las mismas reglas las vuelve a validar el backend (POST /pedidos, AKASH-83).

  AKASH-196 (PO, 22/11): nombres, apellido paterno, apellido materno y dirección son obligatorios,
  y ya no hay recojo: siempre es delivery (siempre se cobra envío). El DNI no se pide.
*/

export const MODALIDAD = 'delivery'; // única modalidad desde AKASH-196

// Límites: nombres + 2 apellidos + 2 espacios = 102 como máximo (la columna cliente.nombre es de 120)
export const NOMBRES_MIN = 2;
export const NOMBRES_MAX = 40;
export const APELLIDO_MIN = 2;
export const APELLIDO_MAX = 30;
export const DIRECCION_MIN = 5;
export const DIRECCION_MAX = 150;
export const REFERENCIA_MAX = 200;

// Solo letras (con tildes, ñ y ü) y un espacio entre palabras: «María José», «De la Cruz».
// \p{L} = cualquier letra Unicode; en Python el equivalente es [^\W\d_].
const SOLO_LETRAS = /^\p{L}+(?: \p{L}+)*$/u;

// Quita espacios de los extremos, deja uno solo entre palabras y une las tildes «sueltas»
// (NFC: algunos teclados escriben «a» + «´» como dos caracteres y no pasarían la regla de letras).
export function limpiarTexto(texto) {
  return String(texto ?? '').normalize('NFC').trim().replace(/\s+/g, ' ');
}

// Nombre completo tal como se guarda y se muestra: «Ana María Quispe Mamani».
export function nombreCompleto({ nombres, apellido_paterno, apellido_materno }) {
  return [nombres, apellido_paterno, apellido_materno].map(limpiarTexto).filter(Boolean).join(' ');
}

// Acepta lo que la gente suele escribir: «987 654 321», «987-654-321» o «+51 987654321».
// Devuelve solo los 9 dígitos (o lo que quede, para que la validación diga qué está mal).
export function normalizarCelular(texto) {
  const digitos = String(texto ?? '').replace(/[\s\-().]/g, '');
  return digitos.replace(/^\+?51(?=\d{9}$)/, '');
}

export const esCelularValido = (celular) => /^9\d{8}$/.test(celular);

// Valida nombres o un apellido. `etiqueta` va dentro del mensaje: «tus nombres», «tu apellido paterno».
function errorDeNombre(valor, { etiqueta, min, max }) {
  const texto = limpiarTexto(valor);
  if (texto === '') return `Escribe ${etiqueta}.`;
  if (!SOLO_LETRAS.test(texto)) return `Escribe ${etiqueta} solo con letras (sin números ni símbolos).`;
  if (texto.length < min) return `Revisa ${etiqueta}: escribe al menos ${min} letras.`;
  if (texto.length > max) return `Revisa ${etiqueta}: máximo ${max} caracteres.`;
  return null;
}

/*
  E4 / E5: valida el formulario. Devuelve { campo: mensaje } solo con los campos que fallan.
  datos: { nombres, apellido_paterno, apellido_materno, celular, distritoId, direccion, referencia }
  distritos: [{ id, nombre, con_cobertura }] de GET /envio/distritos
*/
export function validarDatosPedido(datos, distritos = []) {
  const errores = {};

  const reglas = [
    ['nombres', { etiqueta: 'tus nombres', min: NOMBRES_MIN, max: NOMBRES_MAX }],
    ['apellido_paterno', { etiqueta: 'tu apellido paterno', min: APELLIDO_MIN, max: APELLIDO_MAX }],
    ['apellido_materno', { etiqueta: 'tu apellido materno', min: APELLIDO_MIN, max: APELLIDO_MAX }],
  ];
  for (const [campo, regla] of reglas) {
    const error = errorDeNombre(datos[campo], regla);
    if (error) errores[campo] = error;
  }

  const celular = normalizarCelular(datos.celular);
  if (celular === '') errores.celular = 'Escribe tu número de celular.';
  else if (!/^\d+$/.test(celular)) errores.celular = 'El celular solo puede tener números.';
  else if (!esCelularValido(celular)) errores.celular = 'El celular debe tener 9 dígitos y empezar con 9.';

  const distrito = distritos.find((d) => d.id === Number(datos.distritoId));
  if (!datos.distritoId) errores.distrito = 'Elige tu distrito.';
  else if (!distrito) errores.distrito = 'Elige un distrito de la lista.';
  else if (!distrito.con_cobertura) {
    errores.distrito = `Aún no hacemos delivery a ${distrito.nombre}. Escríbenos por WhatsApp para coordinar.`;
  }

  const direccion = limpiarTexto(datos.direccion);
  if (direccion === '') errores.direccion = 'Escribe tu dirección para el delivery.';
  else if (direccion.length < DIRECCION_MIN) {
    errores.direccion = `Revisa tu dirección: debe tener al menos ${DIRECCION_MIN} caracteres (calle y número).`;
  } else if (direccion.length > DIRECCION_MAX) {
    errores.direccion = `La dirección puede tener hasta ${DIRECCION_MAX} caracteres.`;
  }

  if (limpiarTexto(datos.referencia).length > REFERENCIA_MAX) {
    errores.referencia = `La referencia puede tener hasta ${REFERENCIA_MAX} caracteres.`;
  }

  return errores;
}

/*
  Cuerpo de POST /pedidos. Solo variante y cantidad: el precio lo pone el servidor (E7).
  Manda los campos nuevos (AKASH-83) y, además, `nombre` ya armado: así funciona con el backend
  actual (que pide `nombre` e ignora lo que no conoce) y con el nuevo, sin importar cuál se
  despliegue primero. Cuando AKASH-83 esté en producción, `nombre` se puede dejar de enviar.
*/
export function armarCuerpoPedido(datos, items) {
  const referencia = limpiarTexto(datos.referencia);
  return {
    nombres: limpiarTexto(datos.nombres),
    apellido_paterno: limpiarTexto(datos.apellido_paterno),
    apellido_materno: limpiarTexto(datos.apellido_materno),
    nombre: nombreCompleto(datos),
    celular: normalizarCelular(datos.celular),
    distrito_id: Number(datos.distritoId),
    modalidad_entrega: MODALIDAD,
    direccion: limpiarTexto(datos.direccion),
    referencia: referencia || null,
    items: items.map(({ variante_id, cantidad }) => ({ variante_id, cantidad })),
  };
}

// Costo de envío que se muestra mientras se llena el formulario (el definitivo lo calcula el servidor).
// Devuelve el monto en texto ("10.00") o null si aún no se puede saber.
export function costoEnvioEstimado(distrito) {
  if (distrito?.con_cobertura && distrito.costo_envio != null) {
    return Number(distrito.costo_envio).toFixed(2);
  }
  return null;
}
