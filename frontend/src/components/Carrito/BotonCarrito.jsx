import { useCarrito } from '../../context/carritoContext.js';
import './Carrito.css';

// Botón de la cabecera: abre el panel del carrito y muestra cuántas unidades hay.
function BotonCarrito() {
  const { unidades, abierto, abrir } = useCarrito();
  const texto = unidades === 1 ? '1 unidad' : `${unidades} unidades`;

  return (
    <button
      type="button"
      id="boton-carrito"
      className="BotonCarrito"
      onClick={abrir}
      aria-haspopup="dialog"
      aria-expanded={abierto}
      aria-label={`Abrir carrito, ${texto}`}
    >
      <svg className="BotonCarrito__icono" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
        <path
          d="M6 7h12l-1 13H7L6 7Z M9 7V6a3 3 0 0 1 6 0v1"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      {unidades > 0 && (
        <span className="BotonCarrito__contador" aria-hidden="true">
          {unidades > 99 ? '99+' : unidades}
        </span>
      )}
    </button>
  );
}

export default BotonCarrito;
