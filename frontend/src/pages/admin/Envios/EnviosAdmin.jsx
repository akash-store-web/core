import { useEffect, useState } from 'react';
import AdminLayout from '../../../components/AdminLayout.jsx';
import {
  actualizarZona,
  crearZona,
  guardarDistritosDeZona,
  listarDistritos,
  listarZonas,
} from '../../../services/envioService.js';
import { soles } from '../../../utils/formato.js';
import '../PanelAdmin/PanelAdmin.css';
import './EnviosAdmin.css';

const REGEX_COSTO = /^\d+(\.\d{1,2})?$/;

// Devuelve { error } o { costo: "10.00" }. El costo 0 es válido (envío gratis).
function leerCosto(texto) {
  const limpio = texto.trim().replace(',', '.');
  if (!limpio) return { error: 'Ingresa el costo (0 si el envío es gratis).' };
  if (!REGEX_COSTO.test(limpio)) return { error: 'Usa un monto válido, con hasta 2 decimales.' };
  return { costo: Number(limpio).toFixed(2) };
}

function validarZona(nombre, costoTexto) {
  const errores = {};
  if (!nombre.trim()) errores.nombre = 'Ingresa el nombre de la zona.';
  else if (nombre.trim().length > 60) errores.nombre = 'Máximo 60 caracteres.';
  const costo = leerCosto(costoTexto);
  if (costo.error) errores.costo = costo.error;
  return { errores, costo: costo.costo };
}

// Crear o editar una zona (escenarios 1 y 4).
function FormularioZona({ zona, onGuardar, onCancelar, guardando, errorServidor }) {
  const [nombre, setNombre] = useState(zona?.nombre ?? '');
  const [costo, setCosto] = useState(zona ? String(zona.costo) : '');
  const [errores, setErrores] = useState({});

  function handleSubmit(e) {
    e.preventDefault();
    if (guardando) return;
    const resultado = validarZona(nombre, costo);
    setErrores(resultado.errores);
    if (Object.keys(resultado.errores).length > 0) return;
    onGuardar({ nombre: nombre.trim(), costo: resultado.costo });
  }

  return (
    <form className="EnvioForm" onSubmit={handleSubmit} noValidate>
      <div className="EnvioCampo">
        <label htmlFor={`zona-nombre-${zona?.id ?? 'nueva'}`}>Nombre de la zona</label>
        <input
          id={`zona-nombre-${zona?.id ?? 'nueva'}`}
          type="text"
          maxLength={60}
          placeholder="Lima — motorizado"
          className={errores.nombre ? 'EnvioInvalido' : ''}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        {errores.nombre && <p className="PanelError">{errores.nombre}</p>}
      </div>

      <div className="EnvioCampo">
        <label htmlFor={`zona-costo-${zona?.id ?? 'nueva'}`}>Costo de envío (S/)</label>
        <input
          id={`zona-costo-${zona?.id ?? 'nueva'}`}
          type="text"
          inputMode="decimal"
          placeholder="10.00"
          className={errores.costo ? 'EnvioInvalido' : ''}
          value={costo}
          onChange={(e) => setCosto(e.target.value)}
        />
        {errores.costo ? (
          <p className="PanelError">{errores.costo}</p>
        ) : (
          <p className="EnvioAyuda">Usa 0 si el envío en esta zona es gratis.</p>
        )}
      </div>

      {errorServidor && <p className="PanelError" role="alert">{errorServidor}</p>}

      <div className="EnvioBotones">
        <button type="submit" className="PanelBotonPrimario" disabled={guardando}>
          {guardando ? 'Guardando...' : zona ? 'Guardar cambios' : 'Crear zona'}
        </button>
        {onCancelar && (
          <button type="button" className="PanelBotonSecundario" onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}

// Elegir los distritos de una zona (escenario 1).
function AsignarDistritos({ zona, zonas, distritos, onGuardar, onCancelar, guardando, errorServidor }) {
  const [seleccion, setSeleccion] = useState(
    () => new Set(distritos.filter((d) => d.zona_envio_id === zona.id).map((d) => d.id)),
  );
  const [filtro, setFiltro] = useState('');

  const nombreZona = (id) => zonas.find((z) => z.id === id)?.nombre;
  const visibles = distritos.filter((d) =>
    d.nombre.toLowerCase().includes(filtro.trim().toLowerCase()),
  );

  function alternar(id) {
    setSeleccion((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(id)) siguiente.delete(id);
      else siguiente.add(id);
      return siguiente;
    });
  }

  function guardar() {
    const originales = distritos.filter((d) => d.zona_envio_id === zona.id);
    const agregarIds = distritos
      .filter((d) => seleccion.has(d.id) && d.zona_envio_id !== zona.id)
      .map((d) => d.id);
    const quitar = originales
      .filter((d) => !seleccion.has(d.id))
      .map((d) => ({ id: d.id, nombre: d.nombre }));
    onGuardar(agregarIds, quitar);
  }

  return (
    <div className="EnvioDistritos">
      <input
        type="search"
        className="PanelBuscador"
        placeholder="Buscar distrito"
        aria-label="Buscar distrito"
        value={filtro}
        onChange={(e) => setFiltro(e.target.value)}
      />
      <p className="EnvioAyuda">{seleccion.size} distritos seleccionados para esta zona.</p>

      <ul className="DistritoLista">
        {visibles.map((d) => {
          const enOtraZona = d.zona_envio_id !== null && d.zona_envio_id !== zona.id;
          return (
            <li key={d.id}>
              <label className="DistritoFila">
                <input
                  type="checkbox"
                  checked={seleccion.has(d.id)}
                  onChange={() => alternar(d.id)}
                />
                <span className="DistritoNombre">{d.nombre}</span>
                {enOtraZona && (
                  <span className="Etiqueta Etiqueta--aviso">
                    Hoy en: {nombreZona(d.zona_envio_id)}
                  </span>
                )}
                {d.zona_envio_id === null && (
                  <span className="Etiqueta Etiqueta--alerta">Sin cobertura</span>
                )}
              </label>
            </li>
          );
        })}
        {visibles.length === 0 && <li className="PanelEstado">No hay distritos con ese nombre.</li>}
      </ul>

      {errorServidor && <p className="PanelError" role="alert">{errorServidor}</p>}

      <div className="EnvioBotones">
        <button type="button" className="PanelBotonPrimario" disabled={guardando} onClick={guardar}>
          {guardando ? 'Guardando...' : 'Guardar distritos'}
        </button>
        <button type="button" className="PanelBotonSecundario" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

function EnviosAdmin() {
  const [zonas, setZonas] = useState([]);
  const [distritos, setDistritos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  const [editandoId, setEditandoId] = useState(null);
  const [asignandoId, setAsignandoId] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState('');
  const [aviso, setAviso] = useState('');
  const [cambiandoId, setCambiandoId] = useState(null);
  const [errorAccion, setErrorAccion] = useState('');

  useEffect(() => {
    let activo = true;
    Promise.all([listarZonas(), listarDistritos()])
      .then(([datosZonas, datosDistritos]) => {
        if (!activo) return;
        setZonas(datosZonas);
        setDistritos(datosDistritos);
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
  }, []);

  async function recargar() {
    const [datosZonas, datosDistritos] = await Promise.all([listarZonas(), listarDistritos()]);
    setZonas(datosZonas);
    setDistritos(datosDistritos);
  }

  function cerrarFormularios() {
    setEditandoId(null);
    setAsignandoId(null);
    setErrorForm('');
  }

  async function ejecutar(accion, mensajeExito) {
    setGuardando(true);
    setErrorForm('');
    setAviso('');
    try {
      await accion();
      await recargar();
      if (mensajeExito) setAviso(mensajeExito);
      return true;
    } catch (err) {
      setErrorForm(err.message);
      return false;
    } finally {
      setGuardando(false);
    }
  }

  async function handleCrear(datos) {
    const ok = await ejecutar(
      () => crearZona({ ...datos, activa: true }),
      `Zona «${datos.nombre}» creada. Ahora asígnale sus distritos.`,
    );
    return ok;
  }

  async function handleEditar(zona, datos) {
    const ok = await ejecutar(
      () => actualizarZona(zona.id, { ...datos, activa: zona.activa }),
      `Tarifa actualizada: el checkout ya aplica ${soles(datos.costo)} en «${datos.nombre}».`,
    );
    if (ok) setEditandoId(null);
  }

  async function handleAsignar(zona, agregarIds, quitar) {
    const ok = await ejecutar(
      () => guardarDistritosDeZona(zona.id, agregarIds, quitar),
      `Distritos de «${zona.nombre}» actualizados.`,
    );
    if (ok) setAsignandoId(null);
  }

  async function alternarActiva(zona) {
    setCambiandoId(zona.id);
    setAviso('');
    setErrorForm('');
    setErrorAccion('');
    try {
      await actualizarZona(zona.id, {
        nombre: zona.nombre,
        costo: String(zona.costo),
        activa: !zona.activa,
      });
      await recargar();
    } catch (err) {
      setErrorAccion(err.message);
    } finally {
      setCambiandoId(null);
    }
  }

  const sinCobertura = distritos.filter((d) => !d.con_cobertura).length;

  return (
    <AdminLayout>
      <div className="PanelCabecera">
        <h1 className="PanelTitulo">Zonas de envío</h1>
      </div>

      <p className="EnvioIntro">
        Define a qué distritos llegas y cuánto cuesta el envío en cada zona. Un distrito sin zona
        (o con la zona inactiva) no tiene cobertura: la clienta verá que debe coordinar contigo
        por WhatsApp.
      </p>

      {cargando && <p className="PanelEstado">Cargando zonas...</p>}
      {error && <p className="PanelError" role="alert">{error}</p>}
      {aviso && <p className="PanelAviso" role="status">{aviso}</p>}
      {errorAccion && <p className="PanelError" role="alert">{errorAccion}</p>}

      {!cargando && !error && (
        <>
          <p className="EnvioResumen">
            {distritos.length - sinCobertura} de {distritos.length} distritos con cobertura ·{' '}
            <strong>{sinCobertura} sin cobertura</strong>
          </p>

          <ul className="ZonaLista">
            {zonas.map((zona) => (
              <li key={zona.id} className="ZonaItem">
                <div className="ZonaCabecera">
                  <h2 className="ZonaNombre">{zona.nombre}</h2>
                  <span className="ZonaCosto">{soles(zona.costo)}</span>
                </div>
                <p className="ProductoMeta">
                  {zona.num_distritos} {zona.num_distritos === 1 ? 'distrito' : 'distritos'} ·{' '}
                  {zona.activa ? 'Activa' : 'Inactiva'}
                </p>
                {!zona.activa && (
                  <p className="EnvioAyuda">
                    Mientras esté inactiva, sus distritos no tienen cobertura.
                  </p>
                )}

                <div className="ZonaAcciones">
                  <label className="InterruptorFila">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={zona.activa}
                      aria-label={`${zona.activa ? 'Desactivar' : 'Activar'} ${zona.nombre}`}
                      className={`Interruptor ${zona.activa ? 'Interruptor--on' : ''}`}
                      disabled={cambiandoId === zona.id}
                      onClick={() => alternarActiva(zona)}
                    >
                      <span className="InterruptorPunto" />
                    </button>
                    <span>{zona.activa ? 'Activa' : 'Inactiva'}</span>
                  </label>

                  <div className="EnvioBotones">
                    <button
                      type="button"
                      className="PanelBotonSecundario"
                      onClick={() => {
                        cerrarFormularios();
                        setEditandoId(editandoId === zona.id ? null : zona.id);
                      }}
                    >
                      Editar tarifa
                    </button>
                    <button
                      type="button"
                      className="PanelBotonSecundario"
                      onClick={() => {
                        cerrarFormularios();
                        setAsignandoId(asignandoId === zona.id ? null : zona.id);
                      }}
                    >
                      Distritos
                    </button>
                  </div>
                </div>

                {editandoId === zona.id && (
                  <FormularioZona
                    zona={zona}
                    guardando={guardando}
                    errorServidor={errorForm}
                    onGuardar={(datos) => handleEditar(zona, datos)}
                    onCancelar={cerrarFormularios}
                  />
                )}
                {asignandoId === zona.id && (
                  <AsignarDistritos
                    zona={zona}
                    zonas={zonas}
                    distritos={distritos}
                    guardando={guardando}
                    errorServidor={errorForm}
                    onGuardar={(agregarIds, quitar) => handleAsignar(zona, agregarIds, quitar)}
                    onCancelar={cerrarFormularios}
                  />
                )}
              </li>
            ))}
            {zonas.length === 0 && (
              <li className="PanelEstado">Aún no hay zonas. Crea la primera abajo.</li>
            )}
          </ul>

          <section className="ZonaNueva">
            <h2 className="ZonaNombre">Nueva zona</h2>
            <FormularioZona
              key={zonas.length}
              guardando={guardando && editandoId === null && asignandoId === null}
              errorServidor={editandoId === null && asignandoId === null ? errorForm : ''}
              onGuardar={handleCrear}
            />
          </section>
        </>
      )}
    </AdminLayout>
  );
}

export default EnviosAdmin;