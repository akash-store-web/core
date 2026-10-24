import { useRef, useState } from 'react';
import { PLACEHOLDER } from '../../services/catalogoService.js';

const DESLIZAMIENTO_MINIMO = 40; // px que hay que deslizar el dedo para cambiar de foto

// Galería de la ficha: foto grande + miniaturas.
// fotos: [{ url, es_referencia_escala, generica? }] con la principal primero.
function GaleriaFotos({ fotos, nombre }) {
  const [actual, setActual] = useState(0);
  const [fallidas, setFallidas] = useState([]); // índices de fotos que no cargaron
  const inicioToque = useRef(null);

  const total = fotos.length;
  const varias = total > 1;

  const irA = (indice) => setActual((indice + total) % total); // da la vuelta en los extremos

  const urlDe = (i) => (fallidas.includes(i) ? PLACEHOLDER : fotos[i].url);
  const esGenerica = (i) => fallidas.includes(i) || fotos[i].generica;
  const marcarFallida = (i) =>
    setFallidas((previas) => (previas.includes(i) ? previas : [...previas, i]));

  // Deslizar con el dedo en el celular (las refs solo se leen en los manejadores)
  function alTocar(evento) {
    inicioToque.current = evento.touches[0].clientX;
  }
  function alSoltar(evento) {
    if (inicioToque.current === null || !varias) return;
    const distancia = evento.changedTouches[0].clientX - inicioToque.current;
    inicioToque.current = null;
    if (Math.abs(distancia) < DESLIZAMIENTO_MINIMO) return;
    irA(distancia < 0 ? actual + 1 : actual - 1);
  }

  const fotoActual = fotos[actual];

  return (
    <div className="Galeria" aria-roledescription="galería" aria-label={`Fotos de ${nombre}`}>
      <div className="Galeria__principal" onTouchStart={alTocar} onTouchEnd={alSoltar}>
        <img
          key={actual /* reinicia la animación de entrada al cambiar de foto */}
          src={urlDe(actual)}
          alt={varias ? `${nombre}, foto ${actual + 1} de ${total}` : nombre}
          className={esGenerica(actual) ? 'Galeria__img--generica' : undefined}
          width="600"
          height="800"
          onError={() => marcarFallida(actual)}
        />

        {fotoActual.es_referencia_escala && (
          <span className="Galeria__etiqueta">Referencia de tamaño</span>
        )}

        {varias && (
          <>
            <button
              type="button"
              className="Galeria__flecha Galeria__flecha--anterior"
              onClick={() => irA(actual - 1)}
              aria-label="Foto anterior"
            >
              ‹
            </button>
            <button
              type="button"
              className="Galeria__flecha Galeria__flecha--siguiente"
              onClick={() => irA(actual + 1)}
              aria-label="Foto siguiente"
            >
              ›
            </button>
            <span className="Galeria__contador" aria-hidden="true">
              {actual + 1} / {total}
            </span>
          </>
        )}
      </div>

      {varias && (
        <ul className="Galeria__miniaturas">
          {fotos.map((foto, i) => (
            <li key={`${foto.url}-${i}`}>
              <button
                type="button"
                className="Galeria__miniatura"
                onClick={() => setActual(i)}
                aria-label={`Ver foto ${i + 1} de ${total}`}
                aria-current={i === actual ? 'true' : undefined}
              >
                <img
                  src={urlDe(i)}
                  alt=""
                  className={esGenerica(i) ? 'Galeria__img--generica' : undefined}
                  loading="lazy"
                  width="72"
                  height="96"
                  onError={() => marcarFallida(i)}
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default GaleriaFotos;
