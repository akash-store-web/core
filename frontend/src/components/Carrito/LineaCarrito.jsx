import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PLACEHOLDER } from '../../services/catalogoService.js';
import { soles } from '../../utils/formato.js';
import EnlacePedidoMayor from './EnlacePedidoMayor.jsx';
import SelectorCantidad from './SelectorCantidad.jsx';

const unidadesTexto = (n) => (n === 1 ? '1 unidad disponible' : `${n} unidades disponibles`);

// Si la foto no carga, se usa la genérica (una sola vez, para no entrar en bucle).
function usarGenerica(evento) {
  if (!evento.currentTarget.src.endsWith(PLACEHOLDER)) evento.currentTarget.src = PLACEHOLDER;
}

// Una línea del carrito: foto, nombre, variante, cantidad, subtotal y eliminar.
// `linea` viene de combinarConRevision (lo guardado + lo que dijo el servidor).
function LineaCarrito({ linea, onCambiar, onQuitar, onIrAFicha }) {
  const [error, setError] = useState(null); // { texto, whatsapp }
  const [ocupado, setOcupado] = useState(false);

  const idCampo = `cantidad-${linea.variante_id}`;
  const idError = `cantidad-error-${linea.variante_id}`;
  const fuera = !linea.cuenta; // E8: agotado o ya no disponible
  const porAjustar = linea.estado === 'stock_insuficiente' || linea.estado === 'limite';

  async function cambiar(nueva) {
    setError(null);
    setOcupado(true);
    try {
      const resultado = await onCambiar(linea, nueva);
      // Esc. 3: no alcanza → se rechaza, se dice cuántas hay y se conserva la cantidad
      if (!resultado.ok && resultado.cantidadMaxima > 0) {
        setError({
          texto: `Solo hay ${unidadesTexto(resultado.cantidadMaxima)}. Tu cantidad sigue en ${linea.cantidad}.`,
          whatsapp: false,
        });
      }
    } catch (excepcion) {
      console.error('Cambiar cantidad:', excepcion);
      setError({
        texto: 'No pudimos confirmar la disponibilidad. Revisa tu conexión e inténtalo de nuevo.',
        whatsapp: false,
      });
    } finally {
      setOcupado(false);
    }
  }

  // E5 / E6: lo rechaza el propio selector, antes de ir al servidor
  function alRechazar({ tipo, error: texto }) {
    setError(
      tipo === 'limite'
        ? { texto, whatsapp: true }
        : { texto, whatsapp: false},
    );
  }

  return (
    <article className={`Linea ${fuera ? 'Linea--fuera' : ''}`} aria-labelledby={`linea-${linea.variante_id}`}>
      <img
        className="Linea__foto"
        src={linea.foto || PLACEHOLDER}
        alt=""
        width="80"
        height="80"
        loading="lazy"
        onError={usarGenerica}
      />

      <div className="Linea__info">
        <h3 id={`linea-${linea.variante_id}`} className="Linea__nombre">
          {linea.producto_id ? (
            <Link to={`/catalogo/${linea.producto_id}`} onClick={onIrAFicha}>
              {linea.producto}
            </Link>
          ) : (
            linea.producto
          )}
        </h3>
        {linea.variante && <p className="Linea__variante">{linea.variante}</p>}

        {fuera ? (
          <p className="Linea__estado" role="alert">
            {linea.estado === 'agotado' ? 'Agotado.' : 'Ya no está disponible.'} Quítalo para continuar con
            tu pedido.
          </p>
        ) : (
          <SelectorCantidad
            id={idCampo}
            valor={linea.cantidad}
            onCambiar={cambiar}
            onError={alRechazar}
            etiqueta={`Cantidad de ${linea.producto}${linea.variante ? `, ${linea.variante}` : ''}`}
            ocultarEtiqueta
            ocupado={ocupado}
            idError={error || porAjustar ? idError : undefined}
          />
        )}
      </div>

      <div className="Linea__lado">
        <button
          type="button"
          className="Linea__quitar"
          onClick={() => onQuitar(linea)}
          aria-label={`Eliminar ${linea.producto}${linea.variante ? `, ${linea.variante}` : ''} del carrito`}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        <p className="Linea__precio">
          {fuera ? <span className="Linea__noSuma">No suma</span> : soles(linea.subtotalCentimos / 100)}
        </p>
        {!fuera && linea.cantidad > 1 && linea.precio != null && (
          <p className="Linea__unitario">{soles(linea.precio)} c/u</p>
        )}
      </div>

      {/* Avisos de la línea, a todo el ancho */}
      <div className="Linea__avisos">
        {linea.precioCambio && linea.precioAnterior != null && (
          <p className="Linea__aviso Linea__aviso--info" role="status">
            El precio cambió de {soles(linea.precioAnterior)} a {soles(linea.precio)}.
          </p>
        )}

        {porAjustar && !error && (
          <div id={idError} className="Linea__aviso" role="alert">
            <p>
              {linea.estado === 'limite'
                ? 'Puedes llevar hasta 10 unidades por producto.'
                : `Solo hay ${unidadesTexto(linea.cantidadMaxima)}.`}
            </p>
            {linea.cantidadMaxima > 0 && (
              <button type="button" className="Linea__ajustar" onClick={() => cambiar(linea.cantidadMaxima)}>
                Dejar {linea.cantidadMaxima}
              </button>
            )}
            {linea.estado === 'limite' && <EnlacePedidoMayor producto={linea.producto} variante={linea.variante} />}
          </div>
        )}

        {error && (
          <div id={idError} className="Linea__aviso" role="alert">
            <p>{error.texto}</p>
            {error.whatsapp && <EnlacePedidoMayor producto={linea.producto} variante={linea.variante} />}
          </div>
        )}
      </div>
    </article>
  );
}

export default LineaCarrito;
