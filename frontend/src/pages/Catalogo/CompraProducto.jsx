import { useRef, useState } from 'react';
import { agregarAlCarrito } from '../../services/carritoService.js';
import { soles } from '../../utils/formato.js';

// ¿Qué se elige en este producto? El backend no lo indica, así que se deduce de la
// categoría. Si algún día la API trae un campo "tipo_variante", basta con usarlo aquí.
function queSeElige(categoria = '') {
  if (/incienso|aroma|roll ?on|spray|vela|sahumerio/i.test(categoria)) return { singular: 'aroma', articulo: 'el' };
  if (/anillo|pulsera|collar|arete|dije|cuarzo|piedra|joya/i.test(categoria)) return { singular: 'piedra', articulo: 'la' };
  return { singular: 'opción', articulo: 'una' };
}

// Precio, disponibilidad, selector de variante, propiedades y botón de compra (HU028).
function CompraProducto({ ficha }) {
  const [elegidaId, setElegidaId] = useState(null);
  const [agotadasAhora, setAgotadasAhora] = useState([]); // se agotaron mientras se miraba la ficha (E7)
  const [preciosNuevos, setPreciosNuevos] = useState({}); // precio vigente informado por el servidor
  const [faltaElegir, setFaltaElegir] = useState(false);
  const [aviso, setAviso] = useState(null); // { tipo: 'exito' | 'error', texto }
  const [enviando, setEnviando] = useState(false);
  const grupoRef = useRef(null);

  // Las variantes con lo último que se sabe de ellas
  const variantes = ficha.variantes.map((v) => ({
    ...v,
    precio: preciosNuevos[v.id] ?? v.precio,
    disponible: v.disponible && !agotadasAhora.includes(v.id),
  }));

  // E5: sin variantes reales (solo «Única») no hay selector
  const conSelector = ficha.tiene_variantes && variantes.length > 0;
  const elegida = conSelector
    ? variantes.find((v) => v.id === elegidaId) ?? null
    : variantes[0] ?? null;

  // E9: si ninguna variante tiene existencias, el producto está agotado
  const agotado = !variantes.some((v) => v.disponible);
  const preciosDistintos = new Set(variantes.map((v) => Number(v.precio))).size > 1;
  const tipo = queSeElige(ficha.categoria);

  function elegir(id) {
    setElegidaId(id);
    setFaltaElegir(false);
    setAviso(null);
  }

  async function agregar() {
    setAviso(null);

    // Escenario 1: la selección es obligatoria
    if (!elegida) {
      setFaltaElegir(true);
      grupoRef.current?.querySelector('input:not(:disabled)')?.focus();
      return;
    }

    setEnviando(true);
    try {
      const resultado = await agregarAlCarrito({ ficha, variante: elegida });

      if (resultado.ok) {
        const { item, precioAnterior } = resultado;
        if (precioAnterior) {
          setPreciosNuevos((previos) => ({ ...previos, [elegida.id]: item.precio }));
        }
        setAviso({
          tipo: 'exito',
          texto:
            `Agregado al carrito: ${item.producto}${item.variante ? ` — ${item.variante}` : ''}.` +
            (precioAnterior ? ` El precio se actualizó a ${soles(item.precio)}.` : ''),
        });
        return;
      }

      // E7: el servidor dice que ya no hay stock → se marca como agotada y no se agrega
      if (resultado.estado === 'agotado' || resultado.estado === 'no_disponible') {
        setAgotadasAhora((previas) => [...previas, elegida.id]);
        setElegidaId(null);
        const quedanOtras = variantes.some((v) => v.disponible && v.id !== elegida.id);
        setAviso({
          tipo: 'error',
          texto: conSelector
            ? `Lo sentimos, ${elegida.nombre} se acaba de agotar y no se agregó al carrito.` +
              (quedanOtras ? ` Elige otra ${tipo.singular}.` : '')
            : 'Lo sentimos, este producto se acaba de agotar y no se agregó al carrito.',
        });
        return;
      }

      if (resultado.estado === 'stock_insuficiente') {
        const { cantidadMaxima, enCarrito } = resultado;
        setAviso({
          tipo: 'error',
          texto:
            `Solo ${cantidadMaxima === 1 ? 'queda 1 unidad' : `quedan ${cantidadMaxima} unidades`}` +
            ` y ya ${enCarrito === 1 ? 'tienes 1' : `tienes ${enCarrito}`} en tu carrito.`,
        });
      }
    } catch (error) {
      console.error('Agregar al carrito:', error);
      setAviso({
        tipo: 'error',
        texto: 'No pudimos confirmar la disponibilidad. Revisa tu conexión e inténtalo de nuevo.',
      });
    } finally {
      setEnviando(false);
    }
  }

  // Precio: el de la variante elegida; si aún no se elige, el del producto
  const precioMostrado = elegida ? elegida.precio : ficha.precio;
  const mostrarDesde = !elegida && ficha.precio_desde;

  let textoBoton = 'Agregar al carrito';
  if (agotado) textoBoton = 'Agotado';
  else if (enviando) textoBoton = 'Confirmando disponibilidad…';

  return (
    <div className="Compra">
      <p className="Ficha__precio">
        {mostrarDesde && <span className="Ficha__desde">Desde </span>}
        {soles(precioMostrado)}
      </p>

      <p className={`Ficha__estado ${agotado ? 'Ficha__estado--agotado' : ''}`}>
        {agotado ? 'Agotado' : 'Disponible'}
      </p>

      {conSelector && (
        <fieldset
          ref={grupoRef}
          className={`Selector ${faltaElegir ? 'campo-invalido' : ''}`}
          aria-invalid={faltaElegir || undefined}
          aria-describedby={faltaElegir ? 'selector-error' : undefined}
        >
          <legend className="Selector__titulo">
            Elige {tipo.articulo} {tipo.singular}
            {elegida && <span className="Selector__elegida">: {elegida.nombre}</span>}
          </legend>

          <div className="Selector__opciones">
            {variantes.map((v) => (
              <label
                key={v.id}
                className={[
                  'Selector__opcion',
                  v.id === elegidaId ? 'Selector__opcion--elegida' : '',
                  v.disponible ? '' : 'Selector__opcion--agotada',
                ].join(' ')}
              >
                <input
                  type="radio"
                  name={`variante-${ficha.id}`}
                  value={v.id}
                  checked={v.id === elegidaId}
                  disabled={!v.disponible} /* Escenario 2: la agotada no se puede elegir */
                  onChange={() => elegir(v.id)}
                />
                <span className="Selector__nombre">{v.nombre}</span>
                {preciosDistintos && v.disponible && (
                  <span className="Selector__precio">{soles(v.precio)}</span>
                )}
                {!v.disponible && <span className="Selector__agotada">Agotado</span>}
              </label>
            ))}
          </div>

          {faltaElegir && (
            <p id="selector-error" className="CampoError" role="alert">
              Elige {tipo.articulo} {tipo.singular} antes de
              agregar al carrito.
            </p>
          )}
        </fieldset>
      )}

      {/* Escenario 3: propiedades de la variante elegida (se anuncian al cambiar) */}
      <div className="Compra__propiedades" aria-live="polite">
        {elegida?.propiedades ? (
          <section className="Propiedades" aria-labelledby="propiedades-titulo">
            <h2 id="propiedades-titulo" className="Propiedades__titulo">
              {conSelector ? `Propiedades atribuidas · ${elegida.nombre}` : 'Propiedades atribuidas'}
            </h2>
            <p>{elegida.propiedades}</p>
          </section>
        ) : (
          conSelector && !elegida && !agotado && variantes.some((v) => v.propiedades) && (
            <p className="Compra__pista">
              Elige {tipo.articulo} {tipo.singular} para ver sus
              propiedades.
            </p>
          )
        )}
      </div>

      <button
        type="button"
        className="Compra__boton"
        onClick={agregar}
        disabled={agotado || enviando} /* E9: todo agotado → botón deshabilitado */
        aria-busy={enviando || undefined}
      >
        {textoBoton}
      </button>

      {aviso && (
        <p
          className={`Compra__aviso Compra__aviso--${aviso.tipo}`}
          role={aviso.tipo === 'error' ? 'alert' : 'status'}
        >
          {aviso.texto}
        </p>
      )}
    </div>
  );
}

export default CompraProducto;
