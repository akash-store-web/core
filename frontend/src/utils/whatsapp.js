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
