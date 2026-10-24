import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PLACEHOLDER, obtenerFicha } from '../../services/catalogoService.js';
import CompraProducto from './CompraProducto.jsx';
import GaleriaFotos from './GaleriaFotos.jsx';
import './Catalogo.css';
import './FichaProducto.css';

const AVISO_LENTO_MS = 6000;

// La principal primero. Si el producto no tiene fotos, se usa foto_principal
// (que el backend ya devuelve como imagen genérica).
function fotosDeLaFicha(ficha) {
  const ordenadas = [...ficha.imagenes].sort(
    (a, b) => Number(b.es_principal) - Number(a.es_principal),
  );
  if (ordenadas.length > 0) return ordenadas;
  return [{
    url: ficha.foto_principal || PLACEHOLDER,
    es_referencia_escala: false,
    generica: true,
  }];
}

// Ruta /catalogo/:id
// El `key` hace que, al pasar de un producto a otro, la ficha empiece de cero
// (estado, foto seleccionada, etc.) sin tener que limpiarlo a mano.
function FichaProductoPage() {
  const { id } = useParams();
  return <FichaProducto key={id} id={id} />;
}

function FichaProducto({ id }) {
  // fase: 'cargando' | 'listo' | 'noDisponible' | 'error'
  const [estado, setEstado] = useState({ fase: 'cargando', ficha: null });
  const [lento, setLento] = useState(false);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const avisoLento = setTimeout(() => setLento(true), AVISO_LENTO_MS);

    obtenerFicha(id, { signal: controller.signal })
      .then((ficha) => {
        if (!controller.signal.aborted) setEstado({ fase: 'listo', ficha });
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        if (error.status === 404) {
          setEstado({ fase: 'noDisponible', ficha: null });
          return;
        }
        console.error('Ficha de producto:', error);
        setEstado({ fase: 'error', ficha: null });
      })
      .finally(() => clearTimeout(avisoLento));

    return () => {
      controller.abort();
      clearTimeout(avisoLento);
    };
  }, [id, intento]);

  function reintentar() {
    setEstado({ fase: 'cargando', ficha: null });
    setLento(false);
    setIntento((n) => n + 1);
  }

  const { fase, ficha } = estado;

  if (fase === 'cargando') {
    return (
      <div className="Ficha" aria-busy="true">
        <p className="Catalogo__estadoCarga" role="status">
          {lento
            ? 'Estamos activando la tienda, puede tardar hasta un minuto. Gracias por esperar.'
            : 'Cargando producto…'}
        </p>
        <div className="Ficha__cuerpo" aria-hidden="true">
          <div className="Esqueleto Ficha__esqueletoFoto" />
          <div className="Ficha__info">
            <span className="Esqueleto Esqueleto--corto" />
            <span className="Esqueleto Ficha__esqueletoTitulo" />
            <span className="Esqueleto Esqueleto--corto" />
            <span className="Esqueleto Esqueleto--texto" />
            <span className="Esqueleto Esqueleto--texto" />
          </div>
        </div>
      </div>
    );
  }

  // E6: no existe, fue despublicado o el id no es válido
  if (fase === 'noDisponible') {
    return (
      <div className="Catalogo__aviso" role="alert">
        <title>Producto no disponible | Akash Store Perú</title>
        <p className="Catalogo__avisoTitulo">Este producto ya no está disponible</p>
        <p>Es posible que ya no esté a la venta o que el enlace no sea correcto.</p>
        <Link to="/catalogo" className="Catalogo__boton">
          Ver el catálogo
        </Link>
      </div>
    );
  }

  if (fase === 'error') {
    return (
      <div className="Catalogo__aviso" role="alert">
        <title>Error al cargar | Akash Store Perú</title>
        <p className="Catalogo__avisoTitulo">No pudimos cargar este producto</p>
        <p>Puede ser un problema de conexión. Inténtalo de nuevo en unos segundos.</p>
        <button type="button" className="Catalogo__boton" onClick={reintentar}>
          Reintentar
        </button>
      </div>
    );
  }

  const detalles = [
    ['Material', ficha.material],
    ['Medidas', ficha.medidas],
    ['Peso', ficha.peso_g != null ? `${Number(ficha.peso_g)} g` : null],
  ].filter(([, valor]) => valor);

  return (
    <article className="Ficha">
      <title>{`${ficha.nombre} | Akash Store Perú`}</title>

      <Link to="/catalogo" className="Ficha__volver">
        ← Volver al catálogo
      </Link>

      <div className="Ficha__cuerpo">
        <GaleriaFotos fotos={fotosDeLaFicha(ficha)} nombre={ficha.nombre} />

        <div className="Ficha__info">
          <p className="Ficha__categoria">{ficha.categoria}</p>
          <h1 className="Ficha__nombre">{ficha.nombre}</h1>

          {/* Precio, disponibilidad, selector de variante y botón de compra */}
          <CompraProducto ficha={ficha} />

          {ficha.descripcion && <p className="Ficha__descripcion">{ficha.descripcion}</p>}

          {ficha.es_pieza_natural && (
            <p className="Ficha__nota">
              Pieza natural: cada una es única, por lo que el color, la forma y el tamaño
              pueden variar ligeramente respecto a la foto.
            </p>
          )}

          {detalles.length > 0 && (
            <section className="Ficha__detalles" aria-labelledby="ficha-detalles">
              <h2 id="ficha-detalles" className="Ficha__subtitulo">Detalles</h2>
              <dl>
                {detalles.map(([etiqueta, valor]) => (
                  <div key={etiqueta} className="Ficha__detalle">
                    <dt>{etiqueta}</dt>
                    <dd>{valor}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}
        </div>
      </div>
    </article>
  );
}

export default FichaProductoPage;
