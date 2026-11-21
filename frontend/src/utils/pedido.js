/*
  Lógica pura del pedido por WhatsApp (HU010), sin React: se puede probar en Node.
  Las mismas reglas las vuelve a validar el backend (POST /pedidos).
*/

export const NOMBRE_MIN = 2;
export const NOMBRE_MAX = 80;
export const TEXTO_MAX = 200; // dirección y referencia

// Acepta lo que la gente suele escribir: «987 654 321», «987-654-321» o «+51 987654321».
// Devuelve solo los 9 dígitos (o lo que quede, para que la validación diga qué está mal).
export function normalizarCelular(texto) {
  const digitos = String(texto ?? '').replace(/[\s\-().]/g, '');
  return digitos.replace(/^\+?51(?=\d{9}$)/, '');
}

export const esCelularValido = (celular) => /^9\d{8}$/.test(celular);

/*
  E4 / E5: valida el formulario. Devuelve { campo: mensaje } solo con los campos que fallan.
  datos: { nombre, celular, distritoId, modalidad, direccion, referencia }
  distritos: [{ id, nombre, con_cobertura }] de GET /envio/distritos
*/
export function validarDatosPedido(datos, distritos = []) {
  const errores = {};

  const nombre = (datos.nombre ?? '').trim();
  if (nombre === '') errores.nombre = 'Escribe tu nombre.';
  else if (nombre.length < NOMBRE_MIN) errores.nombre = `Tu nombre debe tener al menos ${NOMBRE_MIN} letras.`;
  else if (nombre.length > NOMBRE_MAX) errores.nombre = `Tu nombre puede tener hasta ${NOMBRE_MAX} caracteres.`;

  const celular = normalizarCelular(datos.celular);
  if (celular === '') errores.celular = 'Escribe tu número de celular.';
  else if (!/^\d+$/.test(celular)) errores.celular = 'El celular solo puede tener números.';
  else if (!esCelularValido(celular)) errores.celular = 'El celular debe tener 9 dígitos y empezar con 9.';

  if (datos.modalidad !== 'delivery' && datos.modalidad !== 'recojo') {
    errores.modalidad = 'Elige cómo quieres recibir tu pedido.';
  }

  const distrito = distritos.find((d) => d.id === Number(datos.distritoId));
  if (!datos.distritoId) errores.distrito = 'Elige tu distrito.';
  else if (!distrito) errores.distrito = 'Elige un distrito de la lista.';
  else if (datos.modalidad === 'delivery' && !distrito.con_cobertura) {
    errores.distrito = `Aún no hacemos delivery a ${distrito.nombre}. Elige «Recojo» o escríbenos por WhatsApp para coordinar.`;
  }

  if ((datos.direccion ?? '').trim().length > TEXTO_MAX) {
    errores.direccion = `La dirección puede tener hasta ${TEXTO_MAX} caracteres.`;
  }
  if ((datos.referencia ?? '').trim().length > TEXTO_MAX) {
    errores.referencia = `La referencia puede tener hasta ${TEXTO_MAX} caracteres.`;
  }

  return errores;
}

// Cuerpo de POST /pedidos. Solo variante y cantidad: el precio lo pone el servidor (E7).
// Dirección y referencia solo viajan con delivery.
export function armarCuerpoPedido(datos, items) {
  const conDelivery = datos.modalidad === 'delivery';
  return {
    nombre: datos.nombre.trim(),
    celular: normalizarCelular(datos.celular),
    distrito_id: Number(datos.distritoId),
    modalidad_entrega: datos.modalidad,
    direccion: conDelivery ? datos.direccion?.trim() || null : null,
    referencia: conDelivery ? datos.referencia?.trim() || null : null,
    items: items.map(({ variante_id, cantidad }) => ({ variante_id, cantidad })),
  };
}

// Costo de envío que se muestra mientras se llena el formulario (el definitivo lo calcula el servidor).
// Devuelve el monto en texto ("10.00"), "0.00" para recojo o null si aún no se puede saber.
export function costoEnvioEstimado(modalidad, distrito) {
  if (modalidad === 'recojo') return '0.00';
  if (modalidad === 'delivery' && distrito?.con_cobertura && distrito.costo_envio != null) {
    return Number(distrito.costo_envio).toFixed(2);
  }
  return null;
}
