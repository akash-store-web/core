import FiltroPrecio from './FiltroPrecio.jsx';
import InterruptorDisponibles from './InterruptorDisponibles.jsx';
import { centimosATexto, hayFiltros } from '../../utils/filtrosCatalogo.js';

// Panel de filtros del catálogo (HU007), a la izquierda en escritorio.
// En celular es un panel que se abre con el botón «Filtrar» y cubre la pantalla.
//
// No guarda estado propio de los filtros: lo aplicado vive en la URL y llega por props.
// Cada cambio se avisa con onCambiar({ ... }) y la página actualiza la URL.
function FiltrosCatalogo({
  categorias,
  conteo,
  filtros,
  totalVisibles,
  onCambiar,
  onLimpiar,
  abierto,
  onCerrar,
  tituloRef,
}) {
  const idCategoria = filtros.categoria?.id ?? null;

  // Escape cierra el panel en celular (en escritorio no hace nada visible).
  function teclado(evento) {
    if (evento.key === 'Escape' && abierto) onCerrar();
  }

  return (
    <>
      <aside
        id="filtros-catalogo"
        className={`Filtros ${abierto ? 'Filtros--abierto' : ''}`}
        aria-labelledby="filtros-titulo"
        onKeyDown={teclado}
      >
        <div className="Filtros__cabecera">
          <h2 id="filtros-titulo" className="Filtros__titulo" tabIndex={-1} ref={tituloRef}>
            Filtrar
          </h2>
          <button type="button" className="Filtros__cerrar" onClick={onCerrar} aria-label="Cerrar filtros">
            ✕
          </button>
        </div>

        <div className="Filtros__contenido">
          {/* HU029: se conserva el interruptor, ahora como un filtro más */}
          <InterruptorDisponibles
            activo={filtros.soloDisponibles}
            onCambio={(activo) => onCambiar({ soloDisponibles: activo })}
          />

          {/* Escenario 1: categoría. Radios nativos = teclado y lector de pantalla sin trabajo extra */}
          <fieldset className="Filtros__grupo">
            <legend className="Filtros__leyenda">Categoría</legend>
            <ul className="Filtros__lista">
              <li>
                <label className="Filtros__opcion">
                  <input
                    type="radio"
                    name="categoria"
                    checked={idCategoria === null}
                    onChange={() => onCambiar({ categoria: null })}
                  />
                  <span>Todas</span>
                </label>
              </li>
              {categorias.map((c) => {
                const cantidad = conteo.get(c.id) ?? 0;
                return (
                  <li key={c.id}>
                    <label className={`Filtros__opcion ${cantidad === 0 ? 'Filtros__opcion--vacia' : ''}`}>
                      <input
                        type="radio"
                        name="categoria"
                        checked={idCategoria === c.id}
                        onChange={() => onCambiar({ categoria: c })}
                      />
                      <span>{c.nombre}</span>
                      <span className="Filtros__cantidad">
                        {cantidad}
                        <span className="sr-only"> productos</span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </fieldset>

          <FiltroPrecio
            key={`${centimosATexto(filtros.precioMin)}-${centimosATexto(filtros.precioMax)}`}
            min={filtros.precioMin}
            max={filtros.precioMax}
            onAplicar={(min, max) => onCambiar({ precioMin: min, precioMax: max })}
          />

          {hayFiltros(filtros) && (
            <button type="button" className="Filtros__limpiar" onClick={onLimpiar}>
              Limpiar filtros
            </button>
          )}
        </div>

        {/* Solo en celular: vuelve al listado */}
        <div className="Filtros__pie">
          <button type="button" className="Filtros__ver" onClick={onCerrar}>
            Ver {totalVisibles} {totalVisibles === 1 ? 'producto' : 'productos'}
          </button>
        </div>
      </aside>

      {/* Fondo oscuro detrás del panel en celular; tocarlo lo cierra */}
      {abierto && <div className="Filtros__fondo" onClick={onCerrar} aria-hidden="true" />}
    </>
  );
}

export default FiltrosCatalogo;