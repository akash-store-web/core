import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCarrito } from '../../context/carritoContext.js';
import {
  aplicarRevision,
  cambiarCantidad,
  obtenerCarrito,
  quitarDelCarrito,
  validarCarrito,
} from '../../services/carritoService.js';
import { combinarConRevision, contarUnidades, resumirCarrito, revisionTrasBajar } from '../../utils/carrito.js';
import { soles } from '../../utils/formato.js';
import LineaCarrito from './LineaCarrito.jsx';
import './Carrito.css';

// Ruta del formulario del pedido (HU010). Mientras no exista, «Continuar» valida el carrito
// y muestra un aviso. Cuando la página esté lista, basta con poner aquí su ruta (por ejemplo '/pedido').
const RUTA_PEDIDO = null;

const indexar = (items = []) => Object.fromEntries(items.map((item) => [item.variante_id, item]));

/*
  Panel lateral del carrito (HU009). Se abre desde la derecha en celular y en computadora.
  Usa <dialog> nativo con showModal(): el navegador ya resuelve el foco atrapado dentro,
  la tecla Esc, el fondo oscuro (::backdrop), que la página de atrás no se pueda usar y
  devolver el foco al botón que lo abrió.
*/
function CarritoPanel() {
  const { abierto, cerrar } = useCarrito();
  const dialogoRef = useRef(null);

  // Sincroniza el estado de React con el <dialog> del navegador (sistema externo).
  useEffect(() => {
    const dialogo = dialogoRef.current;
    if (!dialogo) return;
    if (abierto && !dialogo.open) dialogo.showModal();
    if (!abierto && dialogo.open) dialogo.close();
  }, [abierto]);

  // El navegador devuelve el foco a lo que estaba enfocado antes de abrir. Si no había nada
  // (por ejemplo, «Agregar al carrito» se deshabilitó mientras se confirmaba), el foco se quedaría
  // dentro del panel que se va a desmontar: en ese caso se lleva al botón del carrito de la cabecera.
  function alCerrar(evento) {
    const enfocado = document.activeElement;
    if (!enfocado || enfocado === document.body || evento.currentTarget.contains(enfocado)) {
      document.getElementById('boton-carrito')?.focus();
    }
    cerrar();
  }

  // Clic en el fondo oscuro: el clic llega al propio <dialog> (el contenido ocupa todo el panel).
  function alHacerClic(evento) {
    if (evento.target === evento.currentTarget) cerrar();
  }

  return (
    <dialog
      ref={dialogoRef}
      className="CarritoPanel"
      aria-labelledby="carrito-titulo"
      onClose={alCerrar} /* Esc o close() */
      onClick={alHacerClic}
    >
      {/* Se monta al abrir: cada apertura empieza de cero y vuelve a validar (tarea 2) */}
      {abierto && <ContenidoCarrito />}
    </dialog>
  );
}

function ContenidoCarrito() {
  const { items, cerrar } = useCarrito();
  const navigate = useNavigate();
  const tituloRef = useRef(null);

  // fase: 'revisando' | 'lista' | 'error'. porVariante: lo que respondió el servidor por variante.
  const [revision, setRevision] = useState(() => ({
    fase: items.length > 0 ? 'revisando' : 'lista',
    porVariante: {},
    avisoNatural: null,
  }));
  const [intento, setIntento] = useState(0);
  // fase: 'inicial' | 'validando' | 'bloqueado' | 'precios' | 'listo' | 'error'
  const [continuar, setContinuar] = useState('inicial');
  const [errorGuardar, setErrorGuardar] = useState(null);

  // Tarea 2: al abrir el panel se revalida todo el carrito con el servidor
  // (agotados, despublicados, precios cambiados y datos manipulados).
  useEffect(() => {
    const porRevisar = obtenerCarrito();
    if (porRevisar.length === 0) return undefined;

    const controller = new AbortController();
    validarCarrito(porRevisar, { signal: controller.signal })
      .then((respuesta) => {
        if (controller.signal.aborted) return;
        aplicarRevision(respuesta); // E9: el precio guardado pasa a ser el vigente
        setRevision({
          fase: 'lista',
          porVariante: indexar(respuesta.items),
          avisoNatural: respuesta.aviso_pieza_natural ?? null,
        });
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        console.error('Revisar carrito:', error);
        setRevision((previa) => ({ ...previa, fase: 'error' }));
      });

    return () => controller.abort();
  }, [intento]);

  const lineas = combinarConRevision(items, revision.porVariante);
  const resumen = resumirCarrito(lineas);
  const unidades = contarUnidades(items);

  function reintentar() {
    setRevision((previa) => ({ ...previa, fase: 'revisando' }));
    setIntento((n) => n + 1);
  }

  function actualizarRevision(varianteId, transformar) {
    setRevision((previa) => ({
      ...previa,
      porVariante: { ...previa.porVariante, [varianteId]: transformar(previa.porVariante[varianteId]) },
    }));
  }

  // Esc. 2 y Esc. 3. Devuelve lo que respondió el servicio para que la línea muestre el aviso.
  async function cambiar(linea, nueva) {
    setContinuar('inicial');
    const resultado = await cambiarCantidad(linea.variante_id, nueva);

    if (resultado.ok && resultado.resultado) {
      actualizarRevision(linea.variante_id, () => resultado.resultado); // subió y el servidor lo confirmó
    } else if (resultado.ok) {
      actualizarRevision(linea.variante_id, (previa) => revisionTrasBajar(previa, nueva)); // bajó
    } else if (resultado.resultado) {
      // No alcanzó: la cantidad guardada no cambia, pero sí lo que se sabe del stock
      // (y si se agotó, la línea pasa a «Agotado»).
      actualizarRevision(linea.variante_id, () => revisionTrasBajar(resultado.resultado, linea.cantidad));
    }
    return resultado;
  }

  function quitar(linea) {
    setContinuar('inicial');
    try {
      quitarDelCarrito(linea.variante_id);
      setErrorGuardar(null);
    } catch (error) {
      setErrorGuardar(error.message);
      return;
    }
    // La línea desaparece: el foco vuelve al título para no perderse en la página.
    tituloRef.current?.focus();
  }

  async function alContinuar() {
    setContinuar('validando');
    try {
      const respuesta = await validarCarrito(obtenerCarrito());
      aplicarRevision(respuesta);
      setRevision({
        fase: 'lista',
        porVariante: indexar(respuesta.items),
        avisoNatural: respuesta.aviso_pieza_natural ?? null,
      });

      if (!respuesta.valido) {
        setContinuar('bloqueado'); // E8 / Esc. 3
      } else if (respuesta.items.some((item) => item.precio_cambio)) {
        setContinuar('precios'); // E9: que la clienta vea el total nuevo antes de seguir
      } else if (RUTA_PEDIDO) {
        cerrar();
        navigate(RUTA_PEDIDO);
      } else {
        setContinuar('listo');
      }
    } catch (error) {
      console.error('Continuar con el pedido:', error);
      setContinuar('error');
    }
  }

  const avisosContinuar = {
    bloqueado: { rol: 'alert', texto: 'Revisa los productos marcados antes de continuar.' },
    precios: { rol: 'alert', texto: 'Algunos precios cambiaron. Revisa el total y vuelve a pulsar «Continuar».' },
    listo: { rol: 'status', texto: '¡Tu carrito está listo! Muy pronto podrás enviar tu pedido por WhatsApp desde aquí.' },
    error: { rol: 'alert', texto: 'No pudimos confirmar tu pedido. Revisa tu conexión e inténtalo de nuevo.' },
  };
  const avisoContinuar = avisosContinuar[continuar];
  const bloqueado = !resumen.puedeContinuar || revision.fase === 'revisando';

  return (
    <div className="CarritoPanel__contenido">
      <header className="CarritoPanel__cabecera">
        <h2 id="carrito-titulo" className="CarritoPanel__titulo" ref={tituloRef} tabIndex={-1}>
          Tu carrito
          {unidades > 0 && <span className="CarritoPanel__cuenta"> ({unidades})</span>}
        </h2>
        <button type="button" className="CarritoPanel__cerrar" onClick={cerrar} aria-label="Cerrar carrito">
          <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </header>

      {items.length === 0 ? (
        <div className="CarritoPanel__vacio">
          <p className="CarritoPanel__vacioTitulo">Tu carrito está vacío</p>
          <p>Explora el catálogo y agrega tus piezas favoritas.</p>
          <Link to="/catalogo" className="CarritoPanel__continuar" onClick={cerrar}>
            Ver el catálogo
          </Link>
        </div>
      ) : (
        <>
          <div className="CarritoPanel__cuerpo">
            {revision.fase === 'revisando' && (
              <p className="CarritoPanel__aviso" role="status">
                Confirmando precios y disponibilidad…
              </p>
            )}
            {revision.fase === 'error' && (
              <div className="CarritoPanel__aviso CarritoPanel__aviso--error" role="alert">
                <p>No pudimos confirmar los precios y la disponibilidad. Revisa tu conexión.</p>
                <button type="button" className="CarritoPanel__reintentar" onClick={reintentar}>
                  Reintentar
                </button>
              </div>
            )}
            {resumen.noDisponibles > 0 && (
              <p className="CarritoPanel__aviso CarritoPanel__aviso--error" role="alert">
                {resumen.noDisponibles === 1
                  ? 'Un producto ya no está disponible y no suma al total. Quítalo para continuar.'
                  : `${resumen.noDisponibles} productos ya no están disponibles y no suman al total. Quítalos para continuar.`}
              </p>
            )}
            {resumen.preciosCambiados > 0 && (
              <p className="CarritoPanel__aviso" role="status">
                Algunos precios cambiaron desde que los agregaste. Ya ves los precios actuales.
              </p>
            )}
            {errorGuardar && (
              <p className="CarritoPanel__aviso CarritoPanel__aviso--error" role="alert">
                {errorGuardar}
              </p>
            )}

            <ul className="CarritoPanel__lista">
              {lineas.map((linea) => (
                <li key={linea.variante_id}>
                  <LineaCarrito linea={linea} onCambiar={cambiar} onQuitar={quitar} onIrAFicha={cerrar} />
                </li>
              ))}
            </ul>

            {/* HU006: un solo aviso de pieza natural, como texto plano */}
            {revision.avisoNatural && (
              <p className="CarritoPanel__nota">
                {revision.avisoNatural.texto}
                {revision.avisoNatural.productos?.length > 0 && ` (${revision.avisoNatural.productos.join(', ')})`}
              </p>
            )}
          </div>

          <footer className="CarritoPanel__pie">
            <div className="CarritoPanel__total" aria-live="polite">
              <span>Subtotal</span>
              <strong>{soles(resumen.totalCentimos / 100)}</strong>
            </div>
            <p className="CarritoPanel__envio">El costo de envío se calcula al finalizar el pedido.</p>

            {avisoContinuar && (
              <p
                className={`CarritoPanel__aviso ${avisoContinuar.rol === 'alert' ? 'CarritoPanel__aviso--error' : ''}`}
                role={avisoContinuar.rol}
              >
                {avisoContinuar.texto}
              </p>
            )}

            <button
              type="button"
              className="CarritoPanel__continuar"
              onClick={alContinuar}
              disabled={bloqueado || continuar === 'validando'}
              aria-busy={continuar === 'validando' || undefined}
              aria-describedby={!resumen.puedeContinuar ? 'carrito-bloqueo' : undefined}
            >
              {continuar === 'validando' ? 'Confirmando…' : 'Continuar con el pedido'}
            </button>
            {!resumen.puedeContinuar && (
              <p id="carrito-bloqueo" className="CarritoPanel__bloqueo">
                Quita o ajusta los productos marcados para continuar.
              </p>
            )}
            <button type="button" className="CarritoPanel__seguir" onClick={cerrar}>
              Seguir comprando
            </button>
          </footer>
        </>
      )}
    </div>
  );
}

export default CarritoPanel;
