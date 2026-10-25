import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PLACEHOLDER } from '../../services/catalogoService.js';
import { soles } from '../../utils/formato.js';

// Tarjeta de un producto del catálogo: foto principal, nombre y precio.
// Toda la tarjeta es un enlace a la ficha del producto (HU028).
function ProductoCard({ producto }) {
  // Si la foto falla al cargar, se reemplaza por la imagen genérica.
  const [fotoFallo, setFotoFallo] = useState(false);
  const usarGenerica = fotoFallo || !producto.foto_principal;
  const foto = usarGenerica ? PLACEHOLDER : producto.foto_principal;
  // La genérica es cuadrada: se le permite llenar el marco (no es una foto real que se deba ver completa).
  const esGenerica = usarGenerica || producto.foto_generica;

  return (
    <article className="ProductoCard">
      <Link to={`/catalogo/${producto.id}`} className="ProductoCard__enlace">
        <div className="ProductoCard__foto">
          <img
            src={foto}
            alt={producto.nombre}
            className={esGenerica ? 'ProductoCard__img--generica' : undefined}
            loading="lazy"
            decoding="async"
            width="300"
            height="400"
            onError={() => setFotoFallo(true)}
          />
          {!producto.disponible && <span className="ProductoCard__etiqueta">Agotado</span>}
        </div>

        <div className="ProductoCard__info">
          {/* title muestra el nombre completo al pasar el mouse cuando se recorta */}
          <h2 className="ProductoCard__nombre" title={producto.nombre}>
            {producto.nombre}
          </h2>
          <p className="ProductoCard__precio">
            {producto.precio_desde && <span className="ProductoCard__desde">Desde </span>}
            {soles(producto.precio)}
          </p>
        </div>
      </Link>
    </article>
  );
}

export default ProductoCard;
