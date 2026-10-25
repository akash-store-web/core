import './InterruptorDisponibles.css';

// Interruptor "Ver solo disponibles" del catalogo (HU029).
// No pide nada al servidor: el filtro se aplica en CatalogoPage sobre los productos ya cargados.
function InterruptorDisponibles({ activo, onCambio }) {
  return (
    <div className="Disponibles">
      <label className="Disponibles__etiqueta">
        <input
          type="checkbox"
          role="switch"
          className="Disponibles__entrada"
          checked={activo}
          onChange={(e) => onCambio(e.target.checked)}
        />
        <span className="Disponibles__pista" aria-hidden="true" />
        <span>Ver solo disponibles</span>
      </label>
    </div>
  );
}

export default InterruptorDisponibles;