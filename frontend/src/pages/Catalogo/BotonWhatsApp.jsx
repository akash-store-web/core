import { WHATSAPP_NUMBER } from '../../services/config.js';
import { armarMensajeConsulta, enlaceWhatsApp } from '../../utils/whatsapp.js';

// Botón «Consultar por WhatsApp» de la ficha (HU012). Abre el chat de la tienda con el
// mensaje ya escrito. Es un enlace y no un botón con JavaScript para que el navegador
// no lo bloquee como ventana emergente.
function BotonWhatsApp({ producto, idProducto, variante, sinElegir, agotado }) {
  // E4: sin número válido (AKASH-184) el botón no se muestra
  if (!WHATSAPP_NUMBER) return null;

  const enlaceFicha = `${window.location.origin}/catalogo/${idProducto}`;
  const mensaje = armarMensajeConsulta({
    producto,
    variante,
    sinElegir,
    agotado,
    enlace: enlaceFicha,
  });

  return (
    <a
      className="Compra__whatsapp"
      href={enlaceWhatsApp(WHATSAPP_NUMBER, mensaje)}
      target="_blank"
      rel="noopener noreferrer"
    >
      {agotado ? 'Consultar reposición por WhatsApp' : 'Consultar por WhatsApp'}
    </a>
  );
}

export default BotonWhatsApp;