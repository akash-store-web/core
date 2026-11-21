import './Carrito.css';

// HU006: aviso de pieza natural en el carrito y en el pedido, una sola vez y con los productos
// a los que aplica. `aviso` viene de avisoPiezaNatural() (utils/carrito.js); null → no se muestra.
// El texto se pinta como texto plano (React lo escapa): nunca con dangerouslySetInnerHTML.
function AvisoPiezaNatural({ aviso }) {
  if (!aviso) return null;

  return (
    <section className="AvisoNatural" aria-label="Aviso sobre piezas naturales">
      <svg className="AvisoNatural__icono" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path
          d="M12 3l7 6-7 12L5 9l7-6Z M5 9h14 M12 3v18"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      <div>
        <p className="AvisoNatural__texto">{aviso.texto}</p>
        <p className="AvisoNatural__productos">
          {aviso.productos.length === 1 ? 'Aplica a: ' : 'Aplica a estos productos: '}
          <strong>{aviso.productos.join(', ')}</strong>
        </p>
      </div>
    </section>
  );
}

export default AvisoPiezaNatural;
