import { createContext, useContext } from 'react';

// Contexto del carrito (HU009). El valor lo pone <CarritoProvider> en PublicLayout:
//   items     → líneas guardadas en el navegador (solo referencia; el servidor decide precios)
//   unidades  → total de unidades, para el contador de la cabecera
//   abierto   → si el panel lateral está abierto
//   abrir / cerrar
export const CarritoContext = createContext(null);

export function useCarrito() {
  const contexto = useContext(CarritoContext);
  if (!contexto) throw new Error('useCarrito debe usarse dentro de <CarritoProvider>.');
  return contexto;
}
