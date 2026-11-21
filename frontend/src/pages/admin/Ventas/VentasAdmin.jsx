import { useEffect, useState } from 'react';
import AdminLayout from '../../../components/AdminLayout.jsx';
import { nombreMes, obtenerVentasMes } from '../../../services/ventasService.js';
import { soles } from '../../../utils/formato.js';
import '../PanelAdmin/PanelAdmin.css';
import './Ventas.css';

const PRIMER_MES = { anio: 2026, mes: 9 }; // el backend no tiene registros antes de septiembre de 2026

const conMayuscula = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);

// Meses disponibles en el selector: del mes actual hacia atrás, hasta septiembre de 2026.
function opcionesMeses() {
  const hoy = new Date();
  const lista = [];
  let anio = hoy.getFullYear();
  let mes = hoy.getMonth() + 1;
  while (anio * 12 + mes >= PRIMER_MES.anio * 12 + PRIMER_MES.mes) {
    lista.push({ valor: `${anio}-${String(mes).padStart(2, '0')}`, anio, mes });
    mes -= 1;
    if (mes === 0) {
      mes = 12;
      anio -= 1;
    }
  }
  return lista;
}

// Frase que compara el total del mes con el del mes anterior (escenario 2).
function textoComparacion(actual, anterior) {
  if (!anterior) return null;
  const nombre = nombreMes(anterior.anio, anterior.mes);
  const totalActual = Number(actual.total);
  const totalAnterior = Number(anterior.total);
  if (totalAnterior === 0) return `En ${nombre} no hubo ventas, así que no hay con qué comparar.`;
  const diferencia = totalActual - totalAnterior;
  if (diferencia === 0) return `Igual que en ${nombre}.`;
  const porcentaje = Math.abs((diferencia / totalAnterior) * 100).toFixed(0);
  return `${diferencia > 0 ? 'Subió' : 'Bajó'} ${soles(Math.abs(diferencia))} (${porcentaje}%) frente a ${nombre}.`;
}

function VentasAdmin() {
  const [meses] = useState(opcionesMeses);
  const [periodo, setPeriodo] = useState(() => meses[0].valor);
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let activo = true;
    const [anio, mes] = periodo.split('-').map(Number);
    obtenerVentasMes(anio, mes)
      .then((respuesta) => {
        if (!activo) return;
        setDatos(respuesta);
        setError('');
      })
      .catch((err) => {
        if (!activo) return;
        setDatos(null);
        setError(err.message || 'No se pudieron cargar las ventas.');
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => {
      activo = false;
    };
  }, [periodo]);

  function cambiarMes(e) {
    setCargando(true);
    setPeriodo(e.target.value);
  }

  const comparacion = datos && !datos.sin_ventas ? textoComparacion(datos, datos.mes_anterior) : null;

  return (
    <AdminLayout>
      <div className="PanelCabecera">
        <h1 className="PanelTitulo">Ventas del mes</h1>
      </div>

      <div className="VentasSelector">
        <label htmlFor="ventas-mes">Mes</label>
        <select id="ventas-mes" className="PanelSelect" value={periodo} onChange={cambiarMes}>
          {meses.map((m) => (
            <option key={m.valor} value={m.valor}>
              {conMayuscula(nombreMes(m.anio, m.mes))}
            </option>
          ))}
        </select>
      </div>

      {cargando && <p className="PanelEstado">Cargando ventas...</p>}
      {!cargando && error && <p className="PanelError" role="alert">{error}</p>}

      {!cargando && datos && datos.sin_ventas && <p className="PanelEstado">{datos.mensaje}</p>}

      {!cargando && datos && !datos.sin_ventas && (
        <section aria-label={`Ventas de ${nombreMes(datos.anio, datos.mes)}`}>
          <ul className="VentasTarjetas">
            <li className="VentasTarjeta">
              <span className="VentasEtiqueta">Pedidos</span>
              <strong>{datos.pedidos}</strong>
            </li>
            <li className="VentasTarjeta">
              <span className="VentasEtiqueta">Productos</span>
              <strong>{soles(datos.total_productos)}</strong>
            </li>
            <li className="VentasTarjeta">
              <span className="VentasEtiqueta">Envíos</span>
              <strong>{soles(datos.total_envio)}</strong>
            </li>
            <li className="VentasTarjeta VentasTarjeta--total">
              <span className="VentasEtiqueta">Total</span>
              <strong>{soles(datos.total)}</strong>
            </li>
          </ul>

          {comparacion && <p className="VentasComparacion">{comparacion}</p>}
          {datos.mes_anterior && (
            <p className="VentasAnterior">
              {conMayuscula(nombreMes(datos.mes_anterior.anio, datos.mes_anterior.mes))}: {datos.mes_anterior.pedidos}{' '}
              pedidos · total {soles(datos.mes_anterior.total)}
            </p>
          )}
        </section>
      )}
    </AdminLayout>
  );
}

export default VentasAdmin;
