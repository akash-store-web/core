import { useRef, useState } from 'react';
import { RANGOS_RAPIDOS, centimosATexto, validarRango } from '../../utils/filtrosCatalogo.js';

// Filtro de rango de precio (HU007, Escenario 2 y E4 a E6).
//
// Los campos son un BORRADOR: lo escrito no filtra hasta pulsar «Aplicar».
// Así un rango a medio escribir (o inválido) nunca cambia el listado.
//
// La página lo monta con key = precio aplicado: cuando el precio cambia desde fuera
// (chip ✕, «Limpiar filtros», botón Atrás), React crea uno nuevo y el borrador
// vuelve a leer las props. Así no hace falta un useEffect que copie props al estado.
function FiltroPrecio({ min, max, onAplicar }) {
  const [textoMin, setTextoMin] = useState(centimosATexto(min));
  const [textoMax, setTextoMax] = useState(centimosATexto(max));
  const [errores, setErrores] = useState({ min: null, max: null, rango: null });
  const minRef = useRef(null);
  const maxRef = useRef(null);

  function aplicar(evento) {
    evento.preventDefault();
    const rango = validarRango(textoMin, textoMax);
    setErrores(rango.errores);

    if (!rango.valido) {
      // E4/E5: se avisa y NO se filtra. El foco va al campo que hay que corregir.
      (rango.errores.max && !rango.errores.min ? maxRef : minRef).current?.focus();
      return;
    }
    onAplicar(rango.min, rango.max); // E6: un extremo vacío = sin límite
  }

  // Al corregir un campo se borra su error (y el del rango, que depende de ambos).
  function cambiar(campo, valor) {
    if (campo === 'min') setTextoMin(valor);
    else setTextoMax(valor);
    setErrores((previos) => ({ ...previos, [campo]: null, rango: null }));
  }

  const minInvalido = Boolean(errores.min || errores.rango);
  const maxInvalido = Boolean(errores.max || errores.rango);

  return (
    <fieldset className="Filtros__grupo">
      <legend className="Filtros__leyenda">Precio</legend>

      {/* Atajos: aplican al instante (siempre son rangos válidos) */}
      <div className="Filtros__atajos">
        {RANGOS_RAPIDOS.map((r) => {
          const activo = r.min === min && r.max === max;
          return (
            <button
              key={r.etiqueta}
              type="button"
              className="Filtros__atajo"
              aria-pressed={activo}
              onClick={() => onAplicar(activo ? null : r.min, activo ? null : r.max)}
            >
              {r.etiqueta}
            </button>
          );
        })}
      </div>

      <form className="FiltroPrecio" onSubmit={aplicar} noValidate>
        <div className="FiltroPrecio__campos">
          <div className="FiltroPrecio__campo">
            <label htmlFor="precio-min">Mínimo</label>
            <div className={`FiltroPrecio__entrada ${minInvalido ? 'campo-invalido' : ''}`}>
              <span aria-hidden="true">S/</span>
              <input
                ref={minRef}
                id="precio-min"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                placeholder="0"
                maxLength={12}
                value={textoMin}
                onChange={(e) => cambiar('min', e.target.value)}
                aria-invalid={minInvalido}
                aria-describedby={errores.min ? 'precio-min-error' : errores.rango ? 'precio-rango-error' : undefined}
              />
            </div>
          </div>

          <span className="FiltroPrecio__guion" aria-hidden="true">–</span>

          <div className="FiltroPrecio__campo">
            <label htmlFor="precio-max">Máximo</label>
            <div className={`FiltroPrecio__entrada ${maxInvalido ? 'campo-invalido' : ''}`}>
              <span aria-hidden="true">S/</span>
              <input
                ref={maxRef}
                id="precio-max"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                placeholder="9999"
                maxLength={12}
                value={textoMax}
                onChange={(e) => cambiar('max', e.target.value)}
                aria-invalid={maxInvalido}
                aria-describedby={errores.max ? 'precio-max-error' : errores.rango ? 'precio-rango-error' : undefined}
              />
            </div>
          </div>
        </div>

        {errores.min && <p id="precio-min-error" className="CampoError" role="alert">Mínimo: {errores.min}</p>}
        {errores.max && <p id="precio-max-error" className="CampoError" role="alert">Máximo: {errores.max}</p>}
        {errores.rango && <p id="precio-rango-error" className="CampoError" role="alert">{errores.rango}</p>}

        <button type="submit" className="Filtros__aplicar">Aplicar precio</button>
      </form>
    </fieldset>
  );
}

export default FiltroPrecio;