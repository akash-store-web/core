import { useEffect, useState } from 'react';
import { listarCatalogo } from '../../services/catalogoService.js';
import ProductoCard from './ProductoCard.jsx';
import InterruptorDisponibles from './InterruptorDisponibles.jsx';
import './Catalogo.css';

// Si tarda más que esto, se avisa que el servidor se está activando (E6, Render).
const AVISO_LENTO_MS = 6000;
const TARJETAS_ESQUELETO = 8;

function CatalogoPage() {
  // fase: 'cargando' | 'listo' | 'error'
  const [estado, setEstado] = useState({ fase: 'cargando', productos: [] });
  const [lento, setLento] = useState(false);
  const [soloDisponibles, setSoloDisponibles] = useState(false); // HU029: ocultar los agotados
  const [intento, setIntento] = useState(0); // al cambiar, se vuelve a pedir el catálogo

  useEffect(() => {
    const controller = new AbortController();
    const avisoLento = setTimeout(() => setLento(true), AVISO_LENTO_MS);

    listarCatalogo({ signal: controller.signal })
      .then((productos) => {
        if (!controller.signal.aborted) setEstado({ fase: 'listo', productos });
      })
      .catch((error) => {
        if (controller.signal.aborted) return; // la página se cerró: no hay nada que mostrar
        console.error('Catálogo:', error); // el detalle técnico queda solo para el equipo
        setEstado({ fase: 'error', productos: [] });
      })
      .finally(() => clearTimeout(avisoLento));

    return () => {
      controller.abort();
      clearTimeout(avisoLento);
    };
  }, [intento]);

  // El cambio a "cargando" se hace aquí, en el evento, y no dentro del efecto.
  function reintentar() {
    setEstado({ fase: 'cargando', productos: [] });
    setLento(false);
    setIntento((n) => n + 1);
  }

  const { fase, productos } = estado;
  const visibles = soloDisponibles ? productos.filter((p) => p.disponible) : productos;

  return (
    <section className="Catalogo" aria-labelledby="catalogo-titulo">
      <title>Catálogo | Akash Store Perú</title>

      <header className="Catalogo__cabecera">
        <h1 id="catalogo-titulo" className="PublicTitulo">Catálogo</h1>
        <p className="PublicBajada">
          Cuarzos, joyería de plata e inciensos. Encuentra aquí todo lo que tenemos
          disponible, sin esperar un catálogo por mensaje.
        </p>
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

      {/* Escenario 4: catálogo vacío */}
      {fase === 'listo' && productos.length === 0 && (
        <div className="Catalogo__aviso" role="status">
          <p className="Catalogo__avisoTitulo">Aún no hay productos publicados</p>
          <p>Estamos preparando nuevas piezas. Vuelve pronto.</p>
        </div>
      )}

      {fase === 'listo' && productos.length > 0 && (
        <InterruptorDisponibles activo={soloDisponibles} onCambio={setSoloDisponibles} />
      )}

      {fase === 'listo' && productos.length > 0 && visibles.length === 0 && (
        <div className="Catalogo__aviso" role="status">
          <p className="Catalogo__avisoTitulo">Ahora mismo no hay productos disponibles</p>
          <p>Desactiva el filtro para ver los agotados.</p>
        </div>
      )}

      {/* Escenario 1: listado */}
      {fase === 'listo' && productos.length > 0 && (
        <ul className="Catalogo__grilla">
          {visibles.map((producto) => (
            <li key={producto.id}>
              <ProductoCard producto={producto} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default CatalogoPage;
