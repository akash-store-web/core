import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import {
  enlaceComprobante,
  listarCompras,
  obtenerCompra,
  subirComprobante,
} from '../../../services/comprasService.js';
import { fechaCorta, soles } from '../../../utils/formato.js';
import { tipoRealDeArchivo } from '../../../utils/validators.js';
import '../PanelAdmin/PanelAdmin.css';
import './Compras.css';

const MAX_MB = 5;
const TIPOS_ARCHIVO = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];

const etiquetaTipo = (tipo) => (tipo === 'factura' ? 'Factura' : 'Boleta');

// Detalle de una compra: líneas con su subtotal y el comprobante (ver / adjuntar).
function DetalleCompra({ compraId, onComprobanteCambiado }) {
  const archivoRef = useRef(null);
  const [compra, setCompra] = useState(null);
  const [error, setError] = useState('');
  const [subiendo, setSubiendo] = useState(false);

  useEffect(() => {
    let activo = true;
    obtenerCompra(compraId)
      .then((datos) => {
        if (activo) setCompra(datos);
      })
      .catch((err) => {
        if (activo) setError(err.message);
      });
    return () => {
      activo = false;
    };
  }, [compraId]);

  async function adjuntar(e) {
    const archivo = e.target.files?.[0];
    e.target.value = '';
    if (!archivo) return;

    if (!TIPOS_ARCHIVO.includes(archivo.type) || !(await tipoRealDeArchivo(archivo))) {
      setError('Usa una foto JPG, PNG, WEBP o un PDF válido.');
      return;
    }
    if (archivo.size > MAX_MB * 1024 * 1024) {
      setError(`El archivo pesa más de ${MAX_MB} MB.`);
      return;
    }

    setSubiendo(true);
    setError('');
    try {
      const actualizada = await subirComprobante(compraId, archivo);
      setCompra(actualizada);
      onComprobanteCambiado(compraId);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubiendo(false);
    }
  }

  if (!compra && !error) return <p className="PanelEstado">Cargando detalle...</p>;

  return (
    <div className="CompraDetalle">
      {error && <p className="PanelError" role="alert">{error}</p>}
      {compra && (
        <>
          {compra.proveedor_ruc && <p>RUC del proveedor: {compra.proveedor_ruc}</p>}
          <table className="CompraTabla">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Variante</th>
                <th className="CompraNum">Cant.</th>
                <th className="CompraNum">Costo u.</th>
                <th className="CompraNum">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {compra.items.map((i) => (
                <tr key={i.variante_id}>
                  <td>{i.producto}</td>
                  <td>{i.variante}</td>
                  <td className="CompraNum">{i.cantidad}</td>
                  <td className="CompraNum">{soles(i.costo_unitario)}</td>
                  <td className="CompraNum">{soles(i.subtotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="CompraAdjuntar">
            <input
              ref={archivoRef}
              type="file"
              hidden
              accept="image/jpeg,image/png,image/webp,application/pdf"
              onChange={adjuntar}
            />
            <button
              type="button"
              className="PanelBotonSecundario"
              disabled={subiendo}
              onClick={() => archivoRef.current?.click()}
            >
              {subiendo
                ? 'Subiendo...'
                : compra.tiene_comprobante
                  ? 'Reemplazar comprobante'
                  : 'Adjuntar comprobante'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function ComprasAdmin() {
  const location = useLocation();
  const navigate = useNavigate();

  const [aviso, setAviso] = useState(location.state?.registrada ?? null);
  const [proveedor, setProveedor] = useState('');
  const [q, setQ] = useState('');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [compras, setCompras] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [abiertaId, setAbiertaId] = useState(null);
  const [abriendoId, setAbriendoId] = useState(null);
  const [errorFila, setErrorFila] = useState({});

  // Limpia el estado de navegación para que el aviso no reaparezca al recargar.
  useEffect(() => {
    if (location.state?.registrada) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);

  // Espera un momento después de escribir antes de buscar.
  useEffect(() => {
    const temporizador = setTimeout(() => setQ(proveedor.trim()), 350);
    return () => clearTimeout(temporizador);
  }, [proveedor]);

  useEffect(() => {
    let activo = true;
    listarCompras({ proveedor: q, desde, hasta })
      .then((datos) => {
        if (!activo) return;
        setCompras(datos);
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
  }, [q, desde, hasta]);

  // El enlace del comprobante vence a los 5 minutos: se pide justo al abrirlo.
  // La pestaña se abre ANTES de la petición para que el navegador no la bloquee como ventana emergente.
  async function verComprobante(compra) {
    const ventana = window.open('about:blank', '_blank');
    setAbriendoId(compra.id);
    setErrorFila((prev) => ({ ...prev, [compra.id]: '' }));
    try {
      const { url } = await enlaceComprobante(compra.id);
      if (ventana) ventana.location.href = url;
      else window.location.assign(url);
    } catch (err) {
      ventana?.close();
      setErrorFila((prev) => ({ ...prev, [compra.id]: err.message }));
    } finally {
      setAbriendoId(null);
    }
  }

  function marcarConComprobante(compraId) {
    setCompras((prev) =>
      prev.map((c) => (c.id === compraId ? { ...c, tiene_comprobante: true } : c)),
    );
  }

  return (
    <AdminLayout>
      <div className="PanelCabecera">
        <h1 className="PanelTitulo">Compras</h1>
        <Link to="/adminPanel/compras/nueva" className="PanelBotonPrimario">
          + Registrar compra
        </Link>
      </div>

      {aviso && (
        <div className="PanelAviso" role="status">
          <p>
            Compra <strong>{aviso.numero}</strong> registrada: el stock aumentó en{' '}
            {aviso.unidades} {aviso.unidades === 1 ? 'unidad' : 'unidades'}.
            {aviso.adjunto ? ' Comprobante adjuntado.' : ' Aún no tiene comprobante adjunto.'}
          </p>
          <button type="button" onClick={() => setAviso(null)} aria-label="Cerrar aviso">
            ×
          </button>
        </div>
      )}

      <div className="ComprasFiltros">
        <label>
          Proveedor
          <input
            type="search"
            placeholder="Buscar por proveedor"
            value={proveedor}
            onChange={(e) => setProveedor(e.target.value)}
          />
        </label>
        <label>
          Desde
          <input type="date" value={desde} max={hasta || undefined} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label>
          Hasta
          <input type="date" value={hasta} min={desde || undefined} onChange={(e) => setHasta(e.target.value)} />
        </label>
      </div>

      {cargando && <p className="PanelEstado">Cargando compras...</p>}
      {error && <p className="PanelError" role="alert">{error}</p>}
      {!cargando && !error && compras.length === 0 && (
        <p className="PanelEstado">No hay compras para mostrar.</p>
      )}

      <ul className="ComprasLista">
        {compras.map((c) => (
          <li key={c.id} className="CompraItem">
            <div>
              <p className="CompraTitulo">
                {etiquetaTipo(c.tipo_comprobante)} {c.numero_comprobante}
              </p>
              <p className="CompraMeta">
                {fechaCorta(c.fecha)} · {c.proveedor}
              </p>
              <p className="CompraMeta">
                {c.unidades} {c.unidades === 1 ? 'unidad' : 'unidades'} · {soles(c.total)}
              </p>
              <div className="ProductoEtiquetas">
                {c.tiene_comprobante ? (
                  <span className="Etiqueta">Con comprobante</span>
                ) : (
                  <span className="Etiqueta Etiqueta--aviso">Sin comprobante</span>
                )}
              </div>
            </div>

            <div className="CompraAcciones">
              <button
                type="button"
                className="PanelBotonSecundario"
                aria-expanded={abiertaId === c.id}
                onClick={() => setAbiertaId(abiertaId === c.id ? null : c.id)}
              >
                {abiertaId === c.id ? 'Cerrar detalle' : 'Ver detalle'}
              </button>
              {c.tiene_comprobante && (
                <button
                  type="button"
                  className="PanelBotonSecundario"
                  disabled={abriendoId === c.id}
                  onClick={() => verComprobante(c)}
                >
                  {abriendoId === c.id ? 'Abriendo...' : 'Ver comprobante'}
                </button>
              )}
            </div>

            {errorFila[c.id] && <p className="PanelError" role="alert">{errorFila[c.id]}</p>}
            {abiertaId === c.id && (
              <DetalleCompra compraId={c.id} onComprobanteCambiado={marcarConComprobante} />
            )}
          </li>
        ))}
      </ul>
    </AdminLayout>
  );
}

export default ComprasAdmin;
