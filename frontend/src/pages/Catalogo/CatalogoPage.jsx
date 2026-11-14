import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { listarCatalogo, listarCategorias } from '../../services/catalogoService.js';
import {
  aplicarFiltros,
  categoriasDeProductos,
  contarPorCategoria,
  escribirFiltros,
  hayFiltros,
  leerFiltros,
  limpiarFiltros,
  textoRango,
} from '../../utils/filtrosCatalogo.js';
import ProductoCard from './ProductoCard.jsx';
import FiltrosCatalogo from './FiltrosCatalogo.jsx';
import './Catalogo.css';
import './Filtros.css';

// Si tarda más que esto, se avisa que el servidor se está activando (E6, Render).
const AVISO_LENTO_MS = 6000;
const TARJETAS_ESQUELETO = 8;

// Un valor raro en la URL se muestra recortado en el aviso (nunca se interpreta como HTML: React lo escapa).
const recortar = (texto) => (texto.length > 40 ? `${texto.slice(0, 40)}…` : texto);

function CatalogoPage() {
  // fase: 'cargando' | 'listo' | 'error'
  const [estado, setEstado] = useState({ fase: 'cargando', productos: [], categorias: [] });
  const [lento, setLento] = useState(false);
  const [intento, setIntento] = useState(0); // al cambiar, se vuelve a pedir el catálogo
  const [panelAbierto, setPanelAbierto] = useState(false); // panel de filtros en celular

  // HU007: los filtros aplicados viven en la URL (se pueden compartir y el botón Atrás los deshace)
  const [searchParams, setSearchParams] = useSearchParams();

  const botonFiltrarRef = useRef(null);
  const tituloFiltrosRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    const avisoLento = setTimeout(() => setLento(true), AVISO_LENTO_MS);
    const { signal } = controller;

    Promise.all([
      listarCatalogo({ signal }),
      // Si las categorías fallan, no se pierde el catálogo: se sacan de los productos.
      listarCategorias({ signal }).catch(() => null),
    ])
      .then(([productos, categorias]) => {
        if (signal.aborted) return;
        setEstado({
          fase: 'listo',
          productos,
          categorias: categorias ?? categoriasDeProductos(productos),
        });
      })
      .catch((error) => {
        if (signal.aborted) return; // la página se cerró: no hay nada que mostrar
        console.error('Catálogo:', error); // el detalle técnico queda solo para el equipo
        setEstado({ fase: 'error', productos: [], categorias: [] });
      })
      .finally(() => clearTimeout(avisoLento));

    return () => {
      controller.abort();
      clearTimeout(avisoLento);
    };
  }, [intento]);

  // El cambio a "cargando" se hace aquí, en el evento, y no dentro del efecto.
  function reintentar() {
    setEstado({ fase: 'cargando', productos: [], categorias: [] });
    setLento(false);
    setIntento((n) => n + 1);
  }

  const { fase, productos, categorias } = estado;

  // Todo lo que se muestra se DERIVA de la URL y de los datos; no se copia a otro estado.
  const filtros = useMemo(() => leerFiltros(searchParams, categorias), [searchParams, categorias]);
  const visibles = useMemo(() => aplicarFiltros(productos, filtros), [productos, filtros]);
  const conteo = useMemo(() => contarPorCategoria(productos, filtros), [productos, filtros]);

  function cambiarFiltros(cambios) {
    setSearchParams(escribirFiltros(searchParams, cambios));
  }

  function limpiar() {
    setSearchParams(limpiarFiltros(searchParams));
  }

  // Los refs se usan solo en manejadores de eventos (nunca durante el render).
  function abrirPanel() {
    setPanelAbierto(true);
    // Se espera al siguiente cuadro para que el panel ya sea visible y pueda recibir el foco.
    requestAnimationFrame(() => tituloFiltrosRef.current?.focus());
  }

  function cerrarPanel() {
    setPanelAbierto(false);
    botonFiltrarRef.current?.focus();
  }

  const cantidadFiltros =
    (filtros.categoria ? 1 : 0) +
    (filtros.precioMin != null || filtros.precioMax != null ? 1 : 0) +
    (filtros.soloDisponibles ? 1 : 0);

  const titulo = filtros.categoria?.nombre ?? 'Catálogo';
  const textoCantidad = `${visibles.length} ${visibles.length === 1 ? 'producto' : 'productos'}`;

  return (
    <section className="Catalogo" aria-labelledby="catalogo-titulo">
      <title>{`${filtros.categoria ? `${titulo} | ` : ''}Catálogo | Akash Store Perú`}</title>

      {/* Título centrado, como la referencia: cambia con la categoría elegida */}
      <header className="Catalogo__cabecera">
        <h1 id="catalogo-titulo" className="PublicTitulo">{titulo}</h1>
        {!filtros.categoria && (
          <p className="PublicBajada">
            Cuarzos, joyería de plata e inciensos. Encuentra aquí todo lo que tenemos
            disponible, sin esperar un catálogo por mensaje.
          </p>
        )}
        {fase === 'listo' && productos.length > 0 && (
          <p className="Catalogo__conteo" aria-live="polite">{textoCantidad}</p>
        )}
      </header>

      {/* E6: carga (con aviso si el servidor tarda en despertar) */}
      {fase === 'cargando' && (
        <div aria-busy="true">
          <p className="Catalogo__estadoCarga" role="status">
            {lento
              ? 'Estamos activando el catálogo, puede tardar hasta un minuto. Gracias por esperar.'
              : 'Cargando productos…'}
          </p>
          <ul className="Catalogo__grilla" aria-hidden="true">
            {Array.from({ length: TARJETAS_ESQUELETO }, (_, i) => (
              <li key={i} className="ProductoCard ProductoCard--esqueleto">
                <div className="ProductoCard__foto" />
                <div className="ProductoCard__info">
                  <span className="Esqueleto Esqueleto--texto" />
                  <span className="Esqueleto Esqueleto--corto" />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* E5: error amable con reintento */}
      {fase === 'error' && (
        <div className="Catalogo__aviso" role="alert">
          <p className="Catalogo__avisoTitulo">No pudimos cargar el catálogo</p>
          <p>Puede ser un problema de conexión. Inténtalo de nuevo en unos segundos.</p>
          <button type="button" className="Catalogo__boton" onClick={reintentar}>
            Reintentar
          </button>
        </div>
      )}

      {/* Catálogo vacío (sin filtros que mostrar) */}
      {fase === 'listo' && productos.length === 0 && (
        <div className="Catalogo__aviso" role="status">
          <p className="Catalogo__avisoTitulo">Aún no hay productos publicados</p>
          <p>Estamos preparando nuevas piezas. Vuelve pronto.</p>
        </div>
      )}

      {fase === 'listo' && productos.length > 0 && (
        <div className="Catalogo__cuerpo">
          <FiltrosCatalogo
            categorias={categorias}
            conteo={conteo}
            filtros={filtros}
            totalVisibles={visibles.length}
            onCambiar={cambiarFiltros}
            onLimpiar={limpiar}
            abierto={panelAbierto}
            onCerrar={cerrarPanel}
            tituloRef={tituloFiltrosRef}
          />

          <div className="Catalogo__resultados">
            {/* Celular: botón que abre el panel */}
            <div className="Catalogo__barra">
              <button
                ref={botonFiltrarRef}
                type="button"
                className="Catalogo__filtrar"
                onClick={abrirPanel}
                aria-expanded={panelAbierto}
                aria-controls="filtros-catalogo"
              >
                Filtrar{cantidadFiltros > 0 && ` (${cantidadFiltros})`}
              </button>
            </div>

            {/* E7: categoría que no existe en la URL → se ignora y se avisa, sin error */}
            {filtros.categoriaDesconocida && (
              <p className="Catalogo__nota" role="status">
                No encontramos la categoría «{recortar(filtros.categoriaDesconocida)}». Te mostramos todo el catálogo.
              </p>
            )}
            {/* E4/E5 por URL: un enlace con precios inválidos no filtra */}
            {filtros.precioInvalido && (
              <p className="Catalogo__nota" role="status">
                El rango de precio del enlace no es válido, así que no se aplicó.
              </p>
            )}

            {/* Filtros aplicados: cada uno se quita con su ✕ */}
            {hayFiltros(filtros) && (
              <ul className="Catalogo__chips" aria-label="Filtros aplicados">
                {filtros.categoria && (
                  <li>
                    <button type="button" className="Chip" onClick={() => cambiarFiltros({ categoria: null })}>
                      {filtros.categoria.nombre}
                      <span aria-hidden="true">✕</span>
                      <span className="sr-only">Quitar filtro</span>
                    </button>
                  </li>
                )}
                {(filtros.precioMin != null || filtros.precioMax != null) && (
                  <li>
                    <button
                      type="button"
                      className="Chip"
                      onClick={() => cambiarFiltros({ precioMin: null, precioMax: null })}
                    >
                      {textoRango(filtros.precioMin, filtros.precioMax)}
                      <span aria-hidden="true">✕</span>
                      <span className="sr-only">Quitar filtro</span>
                    </button>
                  </li>
                )}
                {filtros.soloDisponibles && (
                  <li>
                    <button type="button" className="Chip" onClick={() => cambiarFiltros({ soloDisponibles: false })}>
                      Solo disponibles
                      <span aria-hidden="true">✕</span>
                      <span className="sr-only">Quitar filtro</span>
                    </button>
                  </li>
                )}
                <li>
                  <button type="button" className="Chip Chip--limpiar" onClick={limpiar}>
                    Limpiar todo
                  </button>
                </li>
              </ul>
            )}

            {/* Escenario 3: ningún producto cumple los filtros */}
            {visibles.length === 0 ? (
              <div className="Catalogo__aviso" role="status">
                <p className="Catalogo__avisoTitulo">No encontramos productos</p>
                <p>Ningún producto cumple con estos filtros. Prueba con otra categoría o un rango de precio más amplio.</p>
                <button type="button" className="Catalogo__boton" onClick={limpiar}>
                  Limpiar filtros
                </button>
              </div>
            ) : (
              <ul className="Catalogo__grilla">
                {visibles.map((producto) => (
                  <li key={producto.id}>
                    <ProductoCard producto={producto} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default CatalogoPage;