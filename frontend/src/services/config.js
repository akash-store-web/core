export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// true = el frontend funciona con datos simulados, sin backend.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/*
  Número de WhatsApp de la tienda (HU012). Formato internacional sin "+" ni espacios:
  51 + 9 dígitos que empiezan con 9 (por ejemplo 519XXXXXXXX).
  Si falta o no tiene ese formato, WHATSAPP_NUMBER queda en null: el botón de WhatsApp
  no se muestra y el error queda en la consola.
*/
const WHATSAPP_CONFIGURADO = (import.meta.env.VITE_WHATSAPP_NUMBER ?? '').trim();

export function esNumeroWhatsAppValido(numero) {
  return /^519\d{8}$/.test(numero);
}

export const WHATSAPP_NUMBER = esNumeroWhatsAppValido(WHATSAPP_CONFIGURADO)
  ? WHATSAPP_CONFIGURADO
  : null;

if (!WHATSAPP_NUMBER) {
  console.error('WhatsApp: VITE_WHATSAPP_NUMBER no está configurado o no tiene el formato 51 + 9 dígitos que empiezan con 9.');
}