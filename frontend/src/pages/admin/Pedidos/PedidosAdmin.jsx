import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import { listarPedidosAdmin } from '../../../services/pedidosAdminService.js';
import { soles } from '../../../utils/formato.js';
import { ESTADOS_PEDIDO, etiquetaEstado, fechaHoraLima, leerFiltrosPedidos, paginar } from '../../../utils/pedidosAdmin.js';
import EstadoPedido from './EstadoPedido.jsx';
import './Pedidos.css';

const AVISO_LENTO_MS = 6000;

// Ruta /adminPanel/pedidos (HU017, tarea 1): bandeja con filtro por estado, búsqueda y páginas de 20.
function PedidosAdmin() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const { estado, q, pagina, avisos } = useMemo(() => leerFiltrosPedidos(params), [params]);

  const [intento, setIntento] = useState(0);
  // `clave` dice para qué filtros es la lista cargada: si no coincide con los actuales, se está cargando.
  // (Así no hace falta un setState "cargando" dentro del efecto.)
  const clave = `${estado ?? ''}|${q}|${intento}`;
  const [carga, setCarga] = useState({ clave: null, fase: 'cargando', lista: [] });
  const [lentoPara, setLentoPara] = useState(null);

  useEffect(() => {
    let vigente = true;
    const avisoLento = setTimeout(() => setLentoPara(clave), AVISO_LENTO_MS);

    listarPedidosAdmin({ estado, q })
      .then((lista) => {
        if (vigente) setCarga({ clave, fase: 'lista', lista: Array.isArray(lista) ? lista : [] });
      })
      .catch((error) => {
        if (!vigente) return;
        console.error('Bandeja de pedidos:', error);
        setCarga({ clave, fase: 'error', lista: [] });
      })
      .finally(() => clearTimeout(avisoLento));

    return () => {
      vigente = false;
      clearTimeout(avisoLento);
    };
  }, [estado, q, clave]);

  const cargando = carga.clave !== clave;
  const lento = cargando && lentoPara === clave;
  const resultado = paginar(carga.lista, pagina);

  // Cambia los filtros en la URL. Cambiar estado o búsqueda vuelve a la página 1.
  function actualizar(cambios) {
    const nuevos = new URLSearchParams(params);
    for (const [nombre, valor] of Object.entries(cambios)) {
      if (valor) nuevos.set(nombre, String(valor));
      else nuevos.delete(nombre);
    }
    if (!('pagina' in cambios)) nuevos.delete('pagina');
    setParams(nuevos);
  }

  function buscar(evento) {
    evento.preventDefault();
    const texto = new FormData(evento.currentTarget).get('q');
    actualizar({ q: String(texto ?? '').trim() });
  }

  function irAPagina(numero) {
    actualizar({ pagina: numero > 1 ? numero : null });
    window.scrollTo(0, 0);
  }

  let titulo = 'Pedidos';
  if (estado) titulo = `Pedidos · ${etiquetaEstado(estado)}`;

  return (
    <AdminLayout>
      <title>Pedidos | Panel Akash Store</title>
      <div className="Pedidos">
        <header className="Pedidos__cabecera">
          <div>
            <h1 className="Pedidos__titulo">{titulo}</h1>
            <p className="Pedidos__bajada">
              Los pedidos que llegan desde la tienda por WhatsApp, del más reciente al más antiguo.
            </p>
          </div>
        </header>

        {avisos.map((aviso) => (
          <p key={aviso} className="Pedidos__aviso" role="status">
            {aviso}
          </p>
        ))}

        <div className="Pedidos__filtros">
          {/* key={q}: si la búsqueda cambia desde fuera (Atrás, «Ver todos»), el campo se reinicia */}
          <form key={q} className="Pedidos__buscador" role="search" onSubmit={buscar}>
            <label htmlFor="pedidos-buscar" className="sr-only">
              Buscar por número de pedido, nombre o celular
            </label>
            <input
              id="pedidos-buscar"
              name="q"
              type="search"
              defaultValue={q}
              placeholder="Buscar por número (P-0012), nombre o celular"
              maxLength={50}
              autoComplete="off"
            />
            <button type="submit" className="Pedidos__boton">
              Buscar
            </button>
          </form>

          <div className="Pedidos__estados" role="group" aria-label="Filtrar por estado">
            {[{ valor: null, etiqueta: 'Todos' }, ...ESTADOS_PEDIDO].map((opcion) => (
              <button
                key={opcion.etiqueta}
                type="button"
                className={`Pedidos__estado ${estado === opcion.valor ? 'Pedidos__estado--activo' : ''}`}
                aria-pressed={estado === opcion.valor}
                onClick={() => actualizar({ estado: opcion.valor })}
              >
                {opcion.etiqueta}
              </button>
            ))}
          </div>
        </div>

        {cargando && (
          <p className="Pedidos__estadoCarga" role="status">
            {lento
              ? 'Estamos activando el servidor, puede tardar hasta un minuto. Gracias por esperar.'
              : 'Cargando pedidos…'}
          </p>
        )}

        {!cargando && carga.fase === 'error' && (
          <div className="Pedidos__vacio" role="alert">
            <p className="Pedidos__vacioTitulo">No pudimos cargar los pedidos</p>
            <p>Puede ser un problema de conexión. Inténtalo de nuevo.</p>
            <button type="button" className="Pedidos__boton" onClick={() => setIntento((n) => n + 1)}>
              Reintentar
            </button>
          </div>
        )}

        {/* E4 / E5: sin resultados → mensaje, nunca un error */}
        {!cargando && carga.fase === 'lista' && resultado.total === 0 && (
          <div className="Pedidos__vacio" role="status">
            {q ? (
              <>
                <p className="Pedidos__vacioTitulo">No encontramos «{q}»</p>
                <p>
                  {estado
                    ? `No hay pedidos con estado «${etiquetaEstado(estado)}» que coincidan con tu búsqueda.`
                    : 'Revisa el número de pedido (por ejemplo, P-0012), el nombre o el celular.'}
                </p>
              </>
            ) : estado ? (
              <>
                <p className="Pedidos__vacioTitulo">No hay pedidos con estado «{etiquetaEstado(estado)}»</p>
                <p>Prueba con otro estado o revisa todos los pedidos.</p>
              </>
            ) : (
              <>
                <p className="Pedidos__vacioTitulo">Aún no tienes pedidos</p>
                <p>Cuando una clienta envíe su pedido desde la tienda, aparecerá aquí.</p>
              </>
            )}
            {(q || estado) && (
              <button type="button" className="Pedidos__boton" onClick={() => actualizar({ q: null, estado: null })}>
                Ver todos los pedidos
              </button>
            )}
          </div>
        )}

        {!cargando && carga.fase === 'lista' && resultado.total > 0 && (
          <>
            <p className="Pedidos__conteo">
              {resultado.total === 1 ? '1 pedido' : `${resultado.total} pedidos`}
              {resultado.totalPaginas > 1 && ` · mostrando ${resultado.desde} a ${resultado.hasta}`}
            </p>

            <table className="PedidosTabla">
              <thead>
                <tr>
                  <th scope="col">Pedido</th>
                  <th scope="col">Clienta</th>
                  <th scope="col">Fecha</th>
                  <th scope="col" className="PedidosTabla__num">Monto</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {resultado.items.map((pedido) => (
                  <tr key={pedido.id} className="PedidosTabla__fila">
                    <td data-etiqueta="Pedido">
                      {/* El enlace cubre toda la fila (::after), pero solo hay un enlace por fila */}
                      <Link
                        to={`/adminPanel/pedidos/${pedido.id}`}
                        state={{ desde: location.search }}
                        className="PedidosTabla__enlace"
                      >
                        {pedido.numero}
                      </Link>
                    </td>
                    <td data-etiqueta="Clienta" className="PedidosTabla__clienta">
                      {pedido.clienta}
                    </td>
                    <td data-etiqueta="Fecha">{fechaHoraLima(pedido.fecha)}</td>
                    <td data-etiqueta="Monto" className="PedidosTabla__num PedidosTabla__monto">
                      {soles(pedido.total)}
                    </td>
                    <td data-etiqueta="Estado">
                      <EstadoPedido estado={pedido.estado} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* E7: más de 20 → páginas */}
            {resultado.totalPaginas > 1 && (
              <nav className="Pedidos__paginas" aria-label="Páginas de pedidos">
                <button
                  type="button"
                  className="Pedidos__boton Pedidos__boton--secundario"
                  onClick={() => irAPagina(resultado.pagina - 1)}
                  disabled={resultado.pagina === 1}
                >
                  ← Anterior
                </button>
                <span aria-current="page">
                  Página {resultado.pagina} de {resultado.totalPaginas}
                </span>
                <button
                  type="button"
                  className="Pedidos__boton Pedidos__boton--secundario"
                  onClick={() => irAPagina(resultado.pagina + 1)}
                  disabled={resultado.pagina === resultado.totalPaginas}
                >
                  Siguiente →
                </button>
              </nav>
            )}
          </>
        )}
      </div>
    </AdminLayout>
  );
}

export default PedidosAdmin;
