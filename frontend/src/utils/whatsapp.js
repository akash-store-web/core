/*
  Mensajes de consulta por WhatsApp (HU012).
  armarMensajeConsulta devuelve el texto SIN codificar; enlaceWhatsApp lo codifica
  para la URL, así las tildes, la ñ y los símbolos llegan completos y legibles.
*/
export function armarMensajeConsulta({ producto, variante, sinElegir, agotado, enlace }) {
  const saludo = 'Hola, quiero consultar por este producto de Akash Store Perú:';

  // E6: producto agotado, se pregunta por su reposición
  if (agotado) {
    return `${saludo} ${producto}.\n${enlace}\nVeo que está agotado. ¿Lo van a reponer?`;
  }

  // E3: producto con variantes y ninguna elegida, se pregunta por las disponibles
  if (sinElegir) {
    return `${saludo} ${producto}.\n${enlace}\n¿Qué opciones tienen disponibles?`;
  }

  // Escenario 1: producto y, si hay, la variante elegida
  const nombre = variante ? `${producto} (${variante})` : producto;
  return `${saludo} ${nombre}.\n${enlace}`;
}

// Escenarios 1 y 2: wa.me abre la app en el celular y WhatsApp Web en la computadora.
export function enlaceWhatsApp(numero, mensaje) {
  return `https://wa.me/${numero}?text=${encodeURIComponent(mensaje)}`;
}
// HU009 E6: más de 10 unidades de un producto se coordinan por WhatsApp.
export function armarMensajePedidoMayor({ producto, variante }) {
  const nombre = variante ? `${producto} (${variante})` : producto;
  return `Hola, quiero pedir más de 10 unidades de este producto de Akash Store Perú: ${nombre}. ¿Me ayudan con el pedido?`;
}

// HU010 Esc. 1: mensaje del pedido ya registrado. Usa SOLO lo que respondió el servidor
// (número, productos, precios y total), nunca lo guardado en el navegador (E7).
export function armarMensajePedido(pedido) {
  const soles = (monto) => `S/ ${Number(monto).toFixed(2)}`;
  const conDelivery = pedido.modalidad_entrega === 'delivery';

  const productos = pedido.items.map((item) => {
    const variante = item.variante && item.variante !== 'Única' ? ` (${item.variante})` : '';
    return `• ${item.cantidad} × ${item.producto}${variante}: ${soles(item.subtotal)}`;
  });

  const entrega = conDelivery ? `Delivery a ${pedido.distrito}` : `Recojo (vivo en ${pedido.distrito})`;
  const envio = conDelivery ? soles(pedido.costo_envio) : 'sin costo (recojo)';

  return [
    `Hola, quiero hacer este pedido en Akash Store Perú.`,
    '',
    `Pedido: ${pedido.numero}`,
    '',
    ...productos,
    '',
    `Subtotal: ${soles(pedido.subtotal)}`,
    `Envío: ${envio}`,
    `Total: ${soles(pedido.total)}`,
    '',
    'Mis datos:',
    `Nombre: ${pedido.nombre}`,
    `Celular: ${pedido.celular}`,
    `Entrega: ${entrega}`,
    ...(conDelivery && pedido.direccion ? [`Dirección: ${pedido.direccion}`] : []),
    ...(conDelivery && pedido.referencia ? [`Referencia: ${pedido.referencia}`] : []),
  ].join('\n');
}
