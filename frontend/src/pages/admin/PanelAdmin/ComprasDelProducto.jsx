import { useEffect, useState } from 'react';
import { listarComprasDeProducto } from '../../../services/productosService.js';
import './ComprasDelProducto.css';

// La fecha llega como "2026-10-14"; se muestra como "14/10/2026".
function fechaCorta(iso) {
  const [anio, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${anio}`;
}

export default function ComprasDelProducto({ productoId }) {
  const [compras, setCompras] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let activo = true;
    listarComprasDeProducto(productoId)
      .then((datos) => {
        if (activo) setCompras(datos);
      })
      .catch((err) => {
        if (activo) setError(err.message);
      });
    return () => {
      activo = false;
    };
  }, [productoId]);

  return (
    <section className="compras-prod">
      <h3 className="compras-prod__titulo">Compras con las que ingresó su stock</h3>

      {error && <p className="PanelError" role="alert">{error}</p>}
      {!error && compras === null && <p className="PanelEstado">Cargando compras...</p>}
      {compras && compras.length === 0 && (
        <p className="PanelEstado">Este producto aún no tiene compras registradas.</p>
      )}

      {compras && compras.length > 0 && (
        <table className="compras-prod__tabla">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Comprobante</th>
              <th>Variante</th>
              <th className="compras-prod__num">Cantidad</th>
            </tr>
          </thead>
          <tbody>
            {compras.map((c) => (
              <tr key={`${c.compra_id}-${c.variante_id}`}>
                <td>{fechaCorta(c.fecha)}</td>
                <td>
                  <span className="compras-prod__tipo">{c.tipo_comprobante}</span> {c.numero_comprobante}
                </td>
                <td>{c.variante}</td>
                <td className="compras-prod__num">{c.cantidad}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}