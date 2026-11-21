import { WHATSAPP_NUMBER } from '../../services/config.js';
import { armarMensajePedidoMayor, enlaceWhatsApp } from '../../utils/whatsapp.js';

// HU009 E6: para más de 10 unidades se sugiere escribir por WhatsApp.
// Sin número configurado (VITE_WHATSAPP_NUMBER) no se muestra, igual que el botón de la ficha.
function EnlacePedidoMayor({ producto, variante }) {
  if (!WHATSAPP_NUMBER) return null;

  return (
    <a
      className="EnlacePedidoMayor"
      href={enlaceWhatsApp(WHATSAPP_NUMBER, armarMensajePedidoMayor({ producto, variante }))}
      target="_blank"
      rel="noopener noreferrer"
    >
      Escríbenos por WhatsApp para pedidos más grandes
    </a>
  );
}

export default EnlacePedidoMayor;
