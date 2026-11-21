import { useState } from 'react';

// Filtro «¿Qué buscas?» por intención (HU008, Escenario 2).
// Pensado para la clienta que no conoce el nombre de la piedra: elige lo que necesita.
//
// `intenciones` = null cuando no se pudieron cargar: el resto del catálogo funciona igual.
// Primero van las que tienen más productos; las que no tienen se ven atenuadas pero se
// pueden elegir (E7 muestra el mensaje con sugerencias).
const VISIBLES_AL_INICIO = 6;

function FiltroIntencion({ intenciones, seleccionada, onCambiar }) {
  const [verTodas, setVerTodas] = useState(false);

  if (intenciones === null) {
    return (
      <fieldset className="Filtros__grupo">
        <legend className="Filtros__leyenda">¿Qué buscas?</legend>
        <p className="Filtros__nota">Por ahora no pudimos cargar las intenciones.</p>
      </fieldset>
    );
  }
  if (intenciones.length === 0) return null;

  const ordenadas = [...intenciones].sort(
    (a, b) => b.productos - a.productos || a.nombre.localeCompare(b.nombre, 'es'),
  );
  // La elegida siempre se ve, aunque esté más abajo de las primeras 6.
  const mostradas = verTodas
    ? ordenadas
    : ordenadas.filter((i, posicion) => posicion < VISIBLES_AL_INICIO || i.id === seleccionada?.id);
  const ocultas = ordenadas.length - mostradas.length;

  return (
    <fieldset className="Filtros__grupo">
      <legend className="Filtros__leyenda">¿Qué buscas?</legend>
      <ul className="Filtros__lista" id="lista-intenciones">
        <li>
          <label className="Filtros__opcion">
            <input
              type="radio"
              name="intencion"
              checked={!seleccionada}
              onChange={() => onCambiar({ intencion: null })}
            />
            <span>Cualquier intención</span>
          </label>
        </li>
        {mostradas.map((i) => (
          <li key={i.id}>
            <label className={`Filtros__opcion ${i.productos === 0 ? 'Filtros__opcion--vacia' : ''}`}>
              <input
                type="radio"
                name="intencion"
                checked={seleccionada?.id === i.id}
                onChange={() => onCambiar({ intencion: i })}
              />
              <span>{i.nombre}</span>
              <span className="Filtros__cantidad">
                {i.productos}
                <span className="sr-only"> productos</span>
              </span>
            </label>
          </li>
        ))}
      </ul>

      {(ocultas > 0 || verTodas) && (
        <button
          type="button"
          className="Filtros__verMas"
          aria-expanded={verTodas}
          aria-controls="lista-intenciones"
          onClick={() => setVerTodas((v) => !v)}
        >
          {verTodas ? 'Ver menos' : `Ver todas (${ordenadas.length})`}
        </button>
      )}
    </fieldset>
  );
}

export default FiltroIntencion;
