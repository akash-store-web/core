import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import {
  ajustarStock,
  cambiarPublicado,
  listarCategorias,
  listarProductos,
  listarVariantes,
} from '../../../services/productosService.js';
import { soles } from '../../../utils/formato.js';
import './PanelAdmin.css';

// HU015: edición de existencias en la fila, con − / + y cantidad exacta.
function FilaVariante({ variante, onCambio }) {
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  async function aplicar(cambio) {
    setGuardando(true);
    setError('');
    try {
      await onCambio(variante, cambio);
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
      setBorrador(null);
    }
  }

  function confirmarExacto() {
    if (borrador === null) return;
    const texto = borrador.trim();
    if (!/^\d+$/.test(texto)) {
      setError('Ingresa un número entero, 0 o más.');
      setBorrador(null);
      return;
    }
    const nueva = Number(texto);
    if (nueva === variante.existencias) {
      setBorrador(null);
      return;
    }
    aplicar({ existencias: nueva });
  }

  return (
    <li className="VarianteFila">
      <span className="VarianteNombre">{variante.nombre}</span>
      <span className="VariantePrecio">{soles(variante.precio_efectivo)}</span>

      <div className="StockControl">
        <button
          type="button"
          aria-label={`Quitar una unidad de ${variante.nombre}`}
          disabled={guardando || variante.existencias <= 0}
          onClick={() => aplicar({ cambio: -1 })}
        >
          −
        </button>
        <input
          type="text"
          inputMode="numeric"
          aria-label={`Existencias de ${variante.nombre}`}
          value={borrador ?? String(variante.existencias)}
          disabled={guardando}
          onFocus={(e) => e.target.select()}
          onChange={(e) => setBorrador(e.target.value)}
          onBlur={confirmarExacto}
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.currentTarget.blur();
          }}
        />
        <button
          type="button"
          aria-label={`Agregar una unidad a ${variante.nombre}`}
          disabled={guardando}
          onClick={() => aplicar({ cambio: 1 })}
        >
          +
        </button>
      </div>

      {variante.agotado && <span className="Etiqueta Etiqueta--alerta">Agotada</span>}
      {error && <p className="PanelError VarianteError" role="alert">{error}</p>}
    </li>
  );
}

// HU027 escenario 4: se señala qué variante está agotada sin afectar a las demás.
function VariantesDetalle({ productoId, onDeltaTotal }) {
  const [variantes, setVariantes] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let activo = true;
    listarVariantes(productoId)
      .then((datos) => {
        if (activo) setVariantes(datos);
      })
      .catch((err) => {
        if (activo) setError(err.message);
      });
    return () => {
      activo = false;
    };
  }, [productoId]);

  async function cambiarStock(variante, cambio) {
    const respuesta = await ajustarStock(variante.id, cambio);
    setVariantes((prev) =>
      prev.map((v) =>
        v.id === variante.id
          ? { ...v, existencias: respuesta.existencias, agotado: respuesta.agotado }
          : v,
      ),
    );
    onDeltaTotal(productoId, respuesta.existencias - variante.existencias);
  }

  if (error) return <p className="PanelError" role="alert">{error}</p>;
  if (!variantes) return <p className="PanelEstado">Cargando existencias...</p>;

  return (
    <ul className="VarianteLista">
      {variantes.map((v) => (
        <FilaVariante key={v.id} variante={v} onCambio={cambiarStock} />
      ))}
    </ul>
  );
}

function PanelAdmin() {
  const location = useLocation();
  const navigate = useNavigate();

  const [aviso, setAviso] = useState(location.state?.creado ?? null);
  const [categorias, setCategorias] = useState([]);
  const [busqueda, setBusqueda] = useState('');
  const [q, setQ] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [productos, setProductos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [erroresFila, setErroresFila] = useState({});
  const [cambiandoId, setCambiandoId] = useState(null);
  const [abiertoId, setAbiertoId] = useState(null);

  // Limpia el estado de navegación para que el aviso no reaparezca al recargar.
  useEffect(() => {
    if (location.state?.creado) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);

  useEffect(() => {
    let activo = true;
    listarCategorias()
      .then((datos) => {
        if (activo) setCategorias(datos);
      })
      .catch(() => {});
    return () => {
      activo = false;
    };
  }, []);

  // Espera un momento después de escribir antes de buscar.
  useEffect(() => {
    const temporizador = setTimeout(() => setQ(busqueda.trim()), 350);
    return () => clearTimeout(temporizador);
  }, [busqueda]);

  useEffect(() => {
    let activo = true;
    listarProductos({ q, categoriaId })
      .then((datos) => {
        if (!activo) return;
        setProductos(datos);
        setError('');
      })
      .catch((err) => {
        if (activo) setError(err.message);
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => {
      activo = false;
    };
  }, [q, categoriaId]);

  // HU016: publicar / despublicar sin eliminar nada.
  async function alternarPublicado(producto) {
    setCambiandoId(producto.id);
    setErroresFila((prev) => ({ ...prev, [producto.id]: '' }));
    try {
      const respuesta = await cambiarPublicado(producto.id, !producto.publicado);
      setProductos((prev) =>
        prev.map((p) => (p.id === producto.id ? { ...p, publicado: respuesta.publicado } : p)),
      );
    } catch (err) {
      setErroresFila((prev) => ({ ...prev, [producto.id]: err.message }));
    } finally {
      setCambiandoId(null);
    }
  }

  // HU015: mantiene al día el total y la etiqueta "Agotado" de la fila.
  function aplicarDeltaTotal(productoId, delta) {
    setProductos((prev) =>
      prev.map((p) => {
        if (p.id !== productoId) return p;
        const total = p.existencias_total + delta;
        return { ...p, existencias_total: total, agotado: total <= 0 };
      }),
    );
  }

  return (
    <AdminLayout>
      <div className="PanelCabecera">
        <h1 className="PanelTitulo">Productos</h1>
        <Link to="/adminPanel/productos/nuevo" className="PanelBotonPrimario">
          + Nuevo producto
        </Link>
      </div>

      {aviso && (
        <div className="PanelAviso" role="status">
          <p>
            Producto «{aviso}» guardado. Quedó <strong>sin publicar</strong>: actívalo cuando
            quieras mostrarlo en el catálogo.
          </p>
          <button type="button" onClick={() => setAviso(null)} aria-label="Cerrar aviso">
            ×
          </button>
        </div>
      )}

      <div className="PanelFiltros">
        <input
          type="search"
          className="PanelBuscador"
          placeholder="Buscar por nombre"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          aria-label="Buscar producto"
        />
        <select
          className="PanelSelect"
          value={categoriaId}
          onChange={(e) => setCategoriaId(e.target.value)}
          aria-label="Filtrar por categoría"
        >
          <option value="">Todas las categorías</option>
          {categorias.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>
      </div>

      {cargando && <p className="PanelEstado">Cargando productos...</p>}
      {error && <p className="PanelError" role="alert">{error}</p>}
      {!cargando && !error && productos.length === 0 && (
        <p className="PanelEstado">No hay productos para mostrar.</p>
      )}

      <ul className="ProductoLista">
        {productos.map((p) => (
          <li key={p.id} className="ProductoItem">
            <img
              className="ProductoFoto"
              src={p.foto_principal}
              alt=""
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = '/placeholder-producto.webp';
              }}
            />

            <div className="ProductoInfo">
              <h2 className="ProductoNombre">{p.nombre}</h2>
              <p className="ProductoMeta">
                {p.categoria} · {soles(p.precio_base)}
              </p>
              <p className="ProductoMeta">
                Existencias: {p.existencias_total} ·{' '}
                {p.num_variantes > 1 ? `${p.num_variantes} variantes` : 'Sin variantes'}
              </p>
              <div className="ProductoEtiquetas">
                {p.agotado && <span className="Etiqueta Etiqueta--alerta">Agotado</span>}
                {p.foto_generica && (
                  <span className="Etiqueta Etiqueta--aviso">Falta subir fotos</span>
                )}
              </div>
            </div>

            <div className="ProductoAcciones">
              <label className="InterruptorFila">
                <button
                  type="button"
                  role="switch"
                  aria-checked={p.publicado}
                  aria-label={`${p.publicado ? 'Despublicar' : 'Publicar'} ${p.nombre}`}
                  className={`Interruptor ${p.publicado ? 'Interruptor--on' : ''}`}
                  disabled={cambiandoId === p.id}
                  onClick={() => alternarPublicado(p)}
                >
                  <span className="InterruptorPunto" />
                </button>
                <span>{p.publicado ? 'Activo' : 'Inactivo'}</span>
              </label>

              <button
                type="button"
                className="PanelBotonSecundario"
                aria-expanded={abiertoId === p.id}
                onClick={() => setAbiertoId(abiertoId === p.id ? null : p.id)}
              >
                {abiertoId === p.id ? 'Cerrar existencias' : 'Existencias y variantes'}
              </button>
            </div>

            {erroresFila[p.id] && (
              <p className="PanelError ProductoFilaCompleta" role="alert">
                {erroresFila[p.id]}
              </p>
            )}
            {abiertoId === p.id && (
              <div className="ProductoFilaCompleta">
                <VariantesDetalle productoId={p.id} onDeltaTotal={aplicarDeltaTotal} />
              </div>
            )}
          </li>
        ))}
      </ul>
    </AdminLayout>
  );
}

export default PanelAdmin;