import { useMemo, useState, useSyncExternalStore } from 'react';
import { CarritoContext } from '../../context/carritoContext.js';
import { obtenerCarrito, suscribirCarrito } from '../../services/carritoService.js';
import { contarUnidades } from '../../utils/carrito.js';

const SIN_ITEMS = []; // misma referencia siempre (lo pide useSyncExternalStore)
const sinItems = () => SIN_ITEMS;

// Comparte el carrito con toda la tienda: la cabecera (contador), la ficha (agregar) y el panel.
// El carrito vive en localStorage; useSyncExternalStore mantiene a React sincronizado con él,
// incluso si se cambia en otra pestaña.
function CarritoProvider({ children }) {
  const items = useSyncExternalStore(suscribirCarrito, obtenerCarrito, sinItems);
  const [abierto, setAbierto] = useState(false);

  const valor = useMemo(
    () => ({
      items,
      unidades: contarUnidades(items),
      abierto,
      abrir: () => setAbierto(true),
      cerrar: () => setAbierto(false),
    }),
    [items, abierto],
  );

  return <CarritoContext value={valor}>{children}</CarritoContext>;
}

export default CarritoProvider;
