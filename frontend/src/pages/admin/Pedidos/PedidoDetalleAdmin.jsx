import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import { esIdValido } from '../../../services/catalogoService.js';
import { obtenerPedidoAdmin } from '../../../services/pedidosAdminService.js';
import { soles } from '../../../utils/formato.js';
import { enlaceChatClienta, etiquetaEstado, fechaHoraLima, nombreVariante } from '../../../utils/pedidosAdmin.js';
import EstadoPedido from './EstadoPedido.jsx';
import './Pedidos.css';

const AVISO_LENTO_MS = 6000;

// "987654321" → "987 654 321" (más fácil de leer y dictar)
const celularLegible = (telefono) => String(telefono ?? '').replace(/^(\d{3})(\d{3})(\d{3})$/, '$1 $2 $3');

// Ruta /adminPanel/pedidos/:id (HU017, tarea 2).
// El `key` hace que al pasar de un pedido a otro el detalle empiece de cero.
function PedidoDetalleAdmin() {
  const { id } = useParams();
  return <DetallePedido key={id} id={id} />;
}

function DetallePedido({ id }) {
  const location = useLocation();
  // Vuelve a la bandeja con los mismos filtros con los que se abrió el pedido
  const volver = `/adminPanel/pedidos${location.state?.desde ?? ''}`;

  // fase: 'cargando' | 'listo' | 'noExiste' | 'error'. Un id inválido ni se consulta (E6).
  const [estado, setEstado] = useState(() => ({ fase: esIdValido(id) ? 'cargando' : 'noExiste', pedido: null }));
  const [lento, setLento] = useState(false);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (!esIdValido(id)) return undefined;
    let vigente = true;
    const avisoLento = setTimeout(() => setLento(true), AVISO_LENTO_MS);

    obtenerPedidoAdmin(id)
      .then((pedido) => {
        if (vigente) setEstado({ fase: 'listo', pedido });
      })
      .catch((error) => {
        if (!vigente) return;
        if (error.status === 404) {
          setEstado({ fase: 'noExiste', pedido: null }); // E6: sin datos
          return;
        }
        console.error('Detalle del pedido:', error);
        setEstado({ fase: 'error', pedido: null });
      })
      .finally(() => clearTimeout(avisoLento));

    return () => {
      vigente = false;
      clearTimeout(avisoLento);
    };
  }, [id, intento]);

  function reintentar() {
    setEstado({ fase: 'cargando', pedido: null });
    setLento(false);
    setIntento((n) => n + 1);
  }

  const enlaceVolver = (
    <Link to={volver} className="PedidoAdmin__volver">
      ← Volver a pedidos
    </Link>
  );

  if (estado.fase === 'cargando') {
    return (
      <AdminLayout>
        {enlaceVolver}
        <p className="Pedidos__estadoCarga" role="status">
          {lento ? 'Estamos activando el servidor, puede tardar hasta un minuto.' : 'Cargando pedido…'}
        </p>
      </AdminLayout>
    );
  }

  if (estado.fase === 'noExiste' || estado.fase === 'error') {
    const noExiste = estado.fase === 'noExiste';
    return (
      <AdminLayout>
        <title>{noExiste ? 'Pedido no encontrado' : 'Error'} | Panel Akash Store</title>
        {enlaceVolver}
        <div className="Pedidos__vacio" role="alert">
          <p className="Pedidos__vacioTitulo">{noExiste ? 'Este pedido no existe' : 'No pudimos cargar el pedido'}</p>
          <p>{noExiste ? 'Revisa el enlace o búscalo por su número en la bandeja.' : 'Puede ser un problema de conexión.'}</p>
          {noExiste ? (
            <Link to="/adminPanel/pedidos" className="Pedidos__boton">
              Ir a la bandeja
            </Link>
          ) : (
            <button type="button" className="Pedidos__boton" onClick={reintentar}>
              Reintentar
            </button>
          )}
        </div>
      </AdminLayout>
    );
  }

  const { pedido } = estado;
  const { clienta } = pedido;
  const delivery = pedido.modalidad_entrega === 'delivery';
  const enlaceWhatsApp = enlaceChatClienta({ telefono: clienta.telefono, nombre: clienta.nombre, numero: pedido.numero });
  const unidades = pedido.items.reduce((suma, item) => suma + item.cantidad, 0);

  return (
    <AdminLayout>
      <title>{`Pedido ${pedido.numero} | Panel Akash Store`}</title>
      {enlaceVolver}

      <header className="PedidoAdmin__cabecera">
        <div>
          <h1 className="Pedidos__titulo">Pedido {pedido.numero}</h1>
          <p className="Pedidos__bajada">Recibido el {fechaHoraLima(pedido.fecha)}</p>
        </div>
        <EstadoPedido estado={pedido.estado} />
      </header>

      <div className="PedidoAdmin__grilla">
        {/* Productos con variante, cantidad y precio del momento del pedido */}
        <section className="PedidoAdmin__tarjeta PedidoAdmin__productos" aria-labelledby="pedido-productos">
          <h2 id="pedido-productos" className="PedidoAdmin__subtitulo">
            Productos <span className="PedidoAdmin__cuenta">({unidades === 1 ? '1 unidad' : `${unidades} unidades`})</span>
          </h2>
          <ul className="PedidoAdmin__items">
            {pedido.items.map((item) => (
              <li key={item.variante_id} className="PedidoAdmin__item">
                <div>
                  <p className="PedidoAdmin__itemNombre">{item.producto}</p>
                  <p className="PedidoAdmin__itemDetalle">
                    {nombreVariante(item.variante) && <span className="PedidoAdmin__variante">{item.variante}</span>}
                    {item.cantidad} × {soles(item.precio_unitario)}
                  </p>
                </div>
                <p className="PedidoAdmin__itemTotal">{soles(item.subtotal)}</p>
              </li>
            ))}
          </ul>
          <dl className="PedidoAdmin__totales">
            <div>
              <dt>Productos</dt>
              <dd>{soles(pedido.subtotal)}</dd>
            </div>
            <div>
              <dt>Envío</dt>
              <dd>{delivery ? soles(pedido.costo_envio) : 'Sin costo (recojo)'}</dd>
            </div>
            <div className="PedidoAdmin__total">
              <dt>Total</dt>
              <dd>{soles(pedido.total)}</dd>
            </div>
          </dl>
          <p className="PedidoAdmin__nota">Los precios son los del momento del pedido.</p>
        </section>

        <div className="PedidoAdmin__lateral">
          <section className="PedidoAdmin__tarjeta" aria-labelledby="pedido-clienta">
            <h2 id="pedido-clienta" className="PedidoAdmin__subtitulo">Clienta</h2>
            <dl className="PedidoAdmin__datos">
              <div>
                <dt>Nombre</dt>
                <dd>{clienta.nombre}</dd>
              </div>
              <div>
                <dt>Celular</dt>
                <dd>{celularLegible(clienta.telefono)}</dd>
              </div>
              {clienta.correo && (
                <div>
                  <dt>Correo</dt>
                  <dd>{clienta.correo}</dd>
                </div>
              )}
            </dl>
            {enlaceWhatsApp ? (
              <a className="PedidoAdmin__whatsapp" href={enlaceWhatsApp} target="_blank" rel="noopener noreferrer">
                <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                  <path
                    d="M4 20l1.3-3.9A8 8 0 1 1 8 19.1L4 20Z M9 9.5c.3 2.2 2.3 4.2 4.5 4.5l1-1 2 .8-.5 1.7c-3.5.2-7.3-3.6-7-7l1.7-.5.8 2-1 1Z"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                  />
                </svg>
                Abrir chat de WhatsApp
              </a>
            ) : (
              <p className="PedidoAdmin__nota">El celular guardado no es válido para abrir WhatsApp.</p>
            )}
          </section>

          <section className="PedidoAdmin__tarjeta" aria-labelledby="pedido-entrega">
            <h2 id="pedido-entrega" className="PedidoAdmin__subtitulo">Entrega</h2>
            <dl className="PedidoAdmin__datos">
              <div>
                <dt>Modalidad</dt>
                <dd>{delivery ? 'Delivery' : 'Recojo (coordinar el punto por WhatsApp)'}</dd>
              </div>
              <div>
                <dt>Distrito</dt>
                <dd>{pedido.distrito ?? '—'}</dd>
              </div>
              {delivery && (
                <>
                  <div>
                    <dt>Dirección</dt>
                    <dd>{clienta.direccion || <span className="PedidoAdmin__falta">No la indicó: pídela por WhatsApp</span>}</dd>
                  </div>
                  <div>
                    <dt>Referencia</dt>
                    <dd>{clienta.referencia || '—'}</dd>
                  </div>
                </>
              )}
            </dl>
          </section>

          <section className="PedidoAdmin__tarjeta" aria-labelledby="pedido-historial">
            <h2 id="pedido-historial" className="PedidoAdmin__subtitulo">Historial</h2>
            <ol className="PedidoAdmin__historial">
              {pedido.historial.map((cambio, indice) => (
                <li key={`${cambio.estado}-${indice}`}>
                  <span className="PedidoAdmin__historialEstado">{etiquetaEstado(cambio.estado)}</span>
                  <span className="PedidoAdmin__historialFecha">
                    {fechaHoraLima(cambio.fecha)} · {cambio.usuario ?? 'Desde la tienda'}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </AdminLayout>
  );
}

export default PedidoDetalleAdmin;
