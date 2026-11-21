import { useState } from 'react';
import { MAX_POR_LINEA, validarCantidad } from '../../utils/carrito.js';
import './Carrito.css';

/*
  Selector de cantidad −  [ 2 ]  + (lo usan la ficha y cada línea del carrito).

  - El campo es un BORRADOR mientras se escribe: se confirma con Enter o al salir del campo.
  - E5: si lo escrito no es un entero de 1 a 10, se rechaza (onError) y vuelve la cantidad anterior.
  - E6: «+» con 10 unidades no sube: avisa el máximo (onError con tipo 'limite').
  - `ocupado`: mientras se confirma con el servidor se ignoran los clics. No se usa `disabled`
    porque un botón deshabilitado pierde el foco y quien usa teclado "se pierde" en la página.
*/
function SelectorCantidad({
  id,
  valor,
  onCambiar,
  onError,
  etiqueta = 'Cantidad',
  ocultarEtiqueta = false,
  ocupado = false,
  idError,
}) {
  const [borrador, setBorrador] = useState(null); // null = no se está escribiendo
  const texto = borrador ?? String(valor);

  function proponer(textoNuevo) {
    if (ocupado) return;
    const resultado = validarCantidad(textoNuevo);
    if (!resultado.ok) {
      onError?.(resultado);
      return;
    }
    if (resultado.valor !== valor) onCambiar(resultado.valor);
  }

  function confirmarBorrador() {
    if (borrador === null) return;
    setBorrador(null); // vuelve a mostrarse `valor` (la anterior si se rechaza)
    proponer(borrador);
  }

  function alPresionarTecla(evento) {
    if (evento.key === 'Enter') {
      evento.preventDefault();
      confirmarBorrador();
    } else if (evento.key === 'Escape' && borrador !== null) {
      // Deshace lo escrito sin cerrar el panel del carrito
      evento.preventDefault();
      evento.stopPropagation();
      setBorrador(null);
    }
  }

  return (
    <div className={`Cantidad ${ocupado ? 'Cantidad--ocupado' : ''}`}>
      <label htmlFor={id} className={ocultarEtiqueta ? 'sr-only' : 'Cantidad__etiqueta'}>
        {etiqueta}
      </label>
      <div className="Cantidad__control" aria-busy={ocupado || undefined}>
        <button
          type="button"
          className="Cantidad__boton"
          onClick={() => {
            if (valor > 1) proponer(String(valor - 1)); // en 1 no baja ni muestra aviso: para quitarlo está ✕
          }}
          aria-label="Quitar una unidad"
          aria-disabled={valor <= 1 || undefined}
        >
          −
        </button>
        <input
          id={id}
          className="Cantidad__campo"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          maxLength={3}
          value={texto}
          onChange={(evento) => setBorrador(evento.target.value)}
          onBlur={confirmarBorrador}
          onKeyDown={alPresionarTecla}
          readOnly={ocupado}
          aria-describedby={idError}
        />
        <button
          type="button"
          className="Cantidad__boton"
          onClick={() => proponer(String(valor + 1))}
          aria-label="Agregar una unidad"
          aria-disabled={valor >= MAX_POR_LINEA || undefined}
        >
          +
        </button>
      </div>
    </div>
  );
}

export default SelectorCantidad;
