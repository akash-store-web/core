import { etiquetaEstado } from '../../../utils/pedidosAdmin.js';

// Etiqueta de color con el estado del pedido (bandeja y detalle).
// El color ayuda, pero el texto siempre está: no se depende solo del color.
function EstadoPedido({ estado }) {
  return <span className={`EstadoPedido EstadoPedido--${estado}`}>{etiquetaEstado(estado)}</span>;
}

export default EstadoPedido;
