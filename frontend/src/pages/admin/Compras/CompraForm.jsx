import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import { listarProductos, listarVariantes } from '../../../services/productosService.js';
import { registrarCompra, subirComprobante } from '../../../services/comprasService.js';
import { fechaCorta, hoyISO, primerDiaMesISO, soles } from '../../../utils/formato.js';
import { esRucValido, tipoRealDeArchivo } from '../../../utils/validators.js';
import '../ProductoForm/ProductoForm.css';
import './Compras.css';

const MAX_MB = 5;
const TIPOS_ARCHIVO = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
// HU033 escenario 2 habla de «adjuntar». Ponlo en true si el equipo decide que es obligatorio.
const COMPROBANTE_OBLIGATORIO = true;

// Límites de sentido común para este rubro (cuarzos, joyería de plata, inciensos). Son una estimación:
// ajústalos con la lista de precios real de la propietaria. El backend acepta hasta 10000 unidades.
const CANTIDAD_MAX = 10000;
const COSTO_MIN = 0.1;
const COSTO_MAX = 1000;

const REGEX_DECIMAL = /^\d+(\.\d{1,2})?$/;
const REGEX_ENTERO = /^\d+$/;

let contador = 0;
const nuevaLinea = () => ({ key: ++contador, productoId: '', varianteId: '', cantidad: '', costo: '' });

const limpiarDecimal = (texto) => texto.trim().replace(',', '.');

// Se calcula en céntimos para evitar errores de redondeo con decimales (0.1 + 0.2).
function totalEnCentimos(lineas) {
  return lineas.reduce((suma, l) => {
    const costo = limpiarDecimal(l.costo);
    const cantidad = l.cantidad.trim();
    if (!REGEX_DECIMAL.test(costo) || !REGEX_ENTERO.test(cantidad)) return suma;
    return suma + Math.round(Number(costo) * 100) * Number(cantidad);
  }, 0);
}

function validar({ datos, lineas, archivo, hoy, desdeMes }) {
  const e = {};
  const proveedor = datos.proveedor.trim();

  if (!proveedor) e.proveedor = 'Ingresa el proveedor.';
  else if (proveedor.length < 2 || proveedor.length > 120) e.proveedor = 'Entre 2 y 120 caracteres.';

  // La factura exige RUC del proveedor; en la boleta es opcional, pero si lo escriben debe ser válido.
  const ruc = datos.proveedor_ruc.trim();
  if (!ruc && datos.tipo_comprobante === 'factura') e.proveedor_ruc = 'La factura necesita el RUC del proveedor.';
  else if (ruc && !esRucValido(ruc)) e.proveedor_ruc = 'RUC no válido: revisa los 11 dígitos.';
  if (!datos.tipo_comprobante) e.tipo_comprobante = 'Elige boleta o factura.';

  const numero = datos.numero_comprobante.trim();
  if (!numero) e.numero_comprobante = 'Ingresa el número del comprobante.';
  else if (numero.length > 30) e.numero_comprobante = 'Máximo 30 caracteres.';

  if (!datos.fecha) e.fecha = 'Ingresa la fecha del comprobante.';
  else if (datos.fecha > hoy) e.fecha = 'La fecha no puede ser futura.';
  else if (datos.fecha < desdeMes) {
    e.fecha = `Solo se registran compras de este mes (desde el ${fechaCorta(desdeMes)}).`;
  }

  const vistas = new Set();
  lineas.forEach((l, i) => {
    if (!l.productoId) e[`linea_${i}_productoId`] = 'Elige el producto.';
    if (l.productoId && !l.varianteId) e[`linea_${i}_varianteId`] = 'Elige la variante.';
    else if (l.varianteId && vistas.has(l.varianteId)) {
      e[`linea_${i}_varianteId`] = 'Esta variante ya está en otra línea: suma las cantidades.';
    }
    if (l.varianteId) vistas.add(l.varianteId);

    const cantidad = l.cantidad.trim();
    if (!REGEX_ENTERO.test(cantidad) || Number(cantidad) < 1 || Number(cantidad) > CANTIDAD_MAX) {
      e[`linea_${i}_cantidad`] = `Entero entre 1 y ${CANTIDAD_MAX}.`;
    }
    const costo = limpiarDecimal(l.costo);
    if (!REGEX_DECIMAL.test(costo)) {
      e[`linea_${i}_costo`] = 'Costo con hasta 2 decimales.';
    } else if (Number(costo) < COSTO_MIN || Number(costo) > COSTO_MAX) {
      e[`linea_${i}_costo`] = `El costo por unidad debe estar entre S/ ${COSTO_MIN.toFixed(2)} y S/ ${COSTO_MAX}.`;
    }
  });

  if (archivo) {
    if (!TIPOS_ARCHIVO.includes(archivo.type)) e.archivo = 'Usa una foto JPG, PNG, WEBP o un PDF.';
    else if (archivo.size > MAX_MB * 1024 * 1024) e.archivo = `El archivo pesa más de ${MAX_MB} MB.`;
  } else if (COMPROBANTE_OBLIGATORIO) {
    e.archivo = 'Adjunta la foto o el PDF del comprobante.';
  }

  return e;
}

function Campo({ id, label, error, obligatorio, ayuda, children }) {
  return (
    <div className="Campo">
      <label htmlFor={id}>
        {label}
        {obligatorio && <span className="CampoObligatorio"> *</span>}
      </label>
      {children}
      {ayuda && !error && <p className="CampoAyuda">{ayuda}</p>}
      {error && <p className="CampoError" role="alert">{error}</p>}
    </div>
  );
}

function CompraForm() {
  const navigate = useNavigate();
  const archivoRef = useRef(null);
  const hoy = hoyISO();
  const desdeMes = primerDiaMesISO();

  const [datos, setDatos] = useState({
    proveedor: '',
    proveedor_ruc: '',
    tipo_comprobante: '',
    numero_comprobante: '',
    fecha: hoy,
  });
  const [lineas, setLineas] = useState(() => [nuevaLinea()]);
  const [archivo, setArchivo] = useState(null);
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [guardando, setGuardando] = useState(false);

  const [productos, setProductos] = useState([]);
  const [errorProductos, setErrorProductos] = useState('');
  const [variantesDe, setVariantesDe] = useState({}); // { productoId: [variantes] }

  // Si la compra ya se guardó pero el comprobante falló, solo queda reintentar el adjunto.
  const [compraGuardada, setCompraGuardada] = useState(null);

  useEffect(() => {
    let activo = true;
    listarProductos()
      .then((lista) => {
        if (activo) setProductos(lista);
      })
      .catch((err) => {
        if (activo) setErrorProductos(err.message);
      });
    return () => {
      activo = false;
    };
  }, []);

  function limpiarError(clave) {
    setErrores((prev) => {
      if (!prev[clave]) return prev;
      const siguiente = { ...prev };
      delete siguiente[clave];
      return siguiente;
    });
  }

  function cambiarDato(campo, valor) {
    setDatos((prev) => ({ ...prev, [campo]: valor }));
    limpiarError(campo);
  }

  /* ---------- Líneas de productos ---------- */

  function cambiarLinea(indice, campo, valor) {
    setLineas((prev) => prev.map((l, i) => (i === indice ? { ...l, [campo]: valor } : l)));
    limpiarError(`linea_${indice}_${campo}`);
  }

  async function elegirProducto(indice, productoId) {
    setLineas((prev) =>
      prev.map((l, i) => (i === indice ? { ...l, productoId, varianteId: '' } : l)),
    );
    limpiarError(`linea_${indice}_productoId`);
    limpiarError(`linea_${indice}_varianteId`);
    if (!productoId || variantesDe[productoId]) return;

    try {
      const variantes = await listarVariantes(Number(productoId));
      setVariantesDe((prev) => ({ ...prev, [productoId]: variantes }));
    } catch (err) {
      setErrorGeneral(`No se pudieron cargar las variantes: ${err.message}`);
    }
  }

  function agregarLinea() {
    setLineas((prev) => [...prev, nuevaLinea()]);
  }

  function quitarLinea(key) {
    setLineas((prev) => prev.filter((l) => l.key !== key));
    // Los errores van por posición: al quitar una fila se recalculan al guardar.
    setErrores((prev) => {
      const siguiente = {};
      Object.keys(prev).forEach((clave) => {
        if (!clave.startsWith('linea_')) siguiente[clave] = prev[clave];
      });
      return siguiente;
    });
  }

  /* ---------- Comprobante ---------- */

  function elegirArchivo(e) {
    setArchivo(e.target.files?.[0] ?? null);
    limpiarError('archivo');
  }

  function quitarArchivo() {
    setArchivo(null);
    if (archivoRef.current) archivoRef.current.value = '';
  }

  /* ---------- Guardar ---------- */

  function aplicarErroresServidor(detalle) {
    const porCampo = {};
    detalle.forEach((item) => {
      const [, campo, indice, subcampo] = item.loc ?? [];
      if (campo === 'items' && typeof indice === 'number') {
        const clave = subcampo === 'variante_id' ? 'varianteId' : subcampo === 'costo_unitario' ? 'costo' : subcampo;
        porCampo[`linea_${indice}_${clave}`] = item.msg;
      } else if (typeof campo === 'string') {
        porCampo[campo] = item.msg;
      }
    });
    setErrores((prev) => ({ ...prev, ...porCampo }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (guardando) return;

    setErrorGeneral('');
    const todos = validar({ datos, lineas, archivo, hoy, desdeMes });
    // El archivo se revisa por dentro (sus primeros bytes), no solo por su extensión.
    if (archivo && !todos.archivo && !(await tipoRealDeArchivo(archivo))) {
      todos.archivo = 'El archivo no es una foto (JPG, PNG, WEBP) ni un PDF válido.';
    }
    // Reintento del adjunto: la compra ya existe, solo se valida el archivo.
    const encontrados = compraGuardada ? (todos.archivo ? { archivo: todos.archivo } : {}) : todos;
    setErrores(encontrados);

    if (Object.keys(encontrados).length > 0) {
      setTimeout(() => document.querySelector('.campo-invalido')?.focus(), 0);
      return;
    }

    setGuardando(true);
    let compra = compraGuardada;
    try {
      if (!compra) {
        compra = await registrarCompra({
          proveedor: datos.proveedor.trim(),
          proveedor_ruc: datos.proveedor_ruc.trim() || null,
          tipo_comprobante: datos.tipo_comprobante,
          numero_comprobante: datos.numero_comprobante.trim(),
          fecha: datos.fecha,
          items: lineas.map((l) => ({
            variante_id: Number(l.varianteId),
            cantidad: Number(l.cantidad.trim()),
            costo_unitario: Number(limpiarDecimal(l.costo)).toFixed(2),
          })),
        });
        setCompraGuardada(compra);
      }
    } catch (err) {
      // Escenario 5: comprobante duplicado → se avisa y no se suma nada.
      if (err.status === 409) {
        setErrores((prev) => ({ ...prev, numero_comprobante: 'Este comprobante ya está registrado.' }));
        setTimeout(() => document.getElementById('campo-numero_comprobante')?.focus(), 0);
      }
      setErrorGeneral(err.message);
      if (Array.isArray(err.detail)) aplicarErroresServidor(err.detail);
      setGuardando(false);
      return;
    }

    try {
      if (archivo) await subirComprobante(compra.id, archivo);
    } catch (err) {
      setErrorGeneral(
        `La compra se registró y el stock ya aumentó, pero no se pudo adjuntar el comprobante: ${err.message}`,
      );
      setGuardando(false);
      return;
    }

    navigate('/adminPanel/compras', {
      state: {
        registrada: {
          numero: compra.numero_comprobante,
          unidades: compra.unidades,
          adjunto: Boolean(archivo),
        },
      },
    });
  }

  const clase = (clave) => (errores[clave] ? 'campo-invalido' : '');
  const total = totalEnCentimos(lineas) / 100;
  const bloqueado = Boolean(compraGuardada);

  return (
    <AdminLayout>
      <div className="FormCabecera">
        <Link to="/adminPanel/compras" className="FormVolver">← Volver a compras</Link>
        <h1 className="FormTitulo">Registrar compra</h1>
      </div>

      <form className="FormProducto" onSubmit={handleSubmit} noValidate>
        {/* Se bloquea todo menos el adjunto cuando la compra ya se guardó */}
        <fieldset className="ComprasBloque" disabled={bloqueado}>
          {/* ---- Comprobante y proveedor (escenario 1) ---- */}
          <fieldset className="FormSeccion">
            <legend>Comprobante</legend>

            <div className="CampoFila">
              <Campo id="campo-tipo_comprobante" label="Tipo" obligatorio error={errores.tipo_comprobante}>
                <select
                  id="campo-tipo_comprobante"
                  className={clase('tipo_comprobante')}
                  value={datos.tipo_comprobante}
                  onChange={(e) => cambiarDato('tipo_comprobante', e.target.value)}
                  aria-invalid={Boolean(errores.tipo_comprobante)}
                >
                  <option value="">Selecciona</option>
                  <option value="boleta">Boleta</option>
                  <option value="factura">Factura</option>
                </select>
              </Campo>

              <Campo
                id="campo-numero_comprobante"
                label="Número"
                obligatorio
                error={errores.numero_comprobante}
                ayuda="Tal como figura en el comprobante. Ej.: F001-000123"
              >
                <input
                  id="campo-numero_comprobante"
                  className={clase('numero_comprobante')}
                  type="text"
                  maxLength={30}
                  value={datos.numero_comprobante}
                  onChange={(e) => cambiarDato('numero_comprobante', e.target.value)}
                  aria-invalid={Boolean(errores.numero_comprobante)}
                />
              </Campo>

              <Campo
                id="campo-fecha"
                label="Fecha del comprobante"
                obligatorio
                error={errores.fecha}
                ayuda="Solo compras de este mes, hasta hoy."
              >
                <input
                  id="campo-fecha"
                  className={clase('fecha')}
                  type="date"
                  min={desdeMes}
                  max={hoy}
                  value={datos.fecha}
                  onChange={(e) => cambiarDato('fecha', e.target.value)}
                  aria-invalid={Boolean(errores.fecha)}
                />
              </Campo>
            </div>

            <div className="CampoFila ComprasFila2">
              <Campo id="campo-proveedor" label="Proveedor" obligatorio error={errores.proveedor}>
                <input
                  id="campo-proveedor"
                  className={clase('proveedor')}
                  type="text"
                  maxLength={120}
                  value={datos.proveedor}
                  onChange={(e) => cambiarDato('proveedor', e.target.value)}
                  aria-invalid={Boolean(errores.proveedor)}
                />
              </Campo>

              <Campo
                id="campo-proveedor_ruc"
                label="RUC del proveedor"
                obligatorio={datos.tipo_comprobante === 'factura'}
                error={errores.proveedor_ruc}
                ayuda="11 dígitos. Obligatorio en facturas."
              >
                <input
                  id="campo-proveedor_ruc"
                  className={clase('proveedor_ruc')}
                  type="text"
                  inputMode="numeric"
                  maxLength={11}
                  value={datos.proveedor_ruc}
                  onChange={(e) => cambiarDato('proveedor_ruc', e.target.value)}
                  aria-invalid={Boolean(errores.proveedor_ruc)}
                />
              </Campo>
            </div>
          </fieldset>

          {/* ---- Productos que ingresan (escenarios 1 y 3) ---- */}
          <fieldset className="FormSeccion">
            <legend>Productos que ingresan</legend>
            <p className="CampoAyuda">
              Al guardar, las existencias de cada variante aumentarán en la cantidad indicada.
            </p>
            {errorProductos && <p className="CampoError" role="alert">{errorProductos}</p>}

            <ul className="VariantesForm">
              {lineas.map((l, i) => {
                const variantes = variantesDe[l.productoId];
                return (
                  <li key={l.key} className="VarianteForm">
                    <div className="VarianteFormTitulo">
                      <strong>Producto {i + 1}</strong>
                      {lineas.length > 1 && (
                        <button type="button" onClick={() => quitarLinea(l.key)}>Quitar</button>
                      )}
                    </div>

                    <div className="CampoFila ComprasFila2">
                      <Campo
                        id={`campo-linea_${i}_productoId`}
                        label="Producto"
                        obligatorio
                        error={errores[`linea_${i}_productoId`]}
                      >
                        <select
                          id={`campo-linea_${i}_productoId`}
                          className={clase(`linea_${i}_productoId`)}
                          value={l.productoId}
                          onChange={(e) => elegirProducto(i, e.target.value)}
                          aria-invalid={Boolean(errores[`linea_${i}_productoId`])}
                        >
                          <option value="">Selecciona un producto</option>
                          {productos.map((p) => (
                            <option key={p.id} value={p.id}>{p.nombre}</option>
                          ))}
                        </select>
                      </Campo>

                      <Campo
                        id={`campo-linea_${i}_varianteId`}
                        label="Variante"
                        obligatorio
                        error={errores[`linea_${i}_varianteId`]}
                      >
                        <select
                          id={`campo-linea_${i}_varianteId`}
                          className={clase(`linea_${i}_varianteId`)}
                          value={l.varianteId}
                          disabled={!l.productoId || !variantes}
                          onChange={(e) => cambiarLinea(i, 'varianteId', e.target.value)}
                          aria-invalid={Boolean(errores[`linea_${i}_varianteId`])}
                        >
                          <option value="">
                            {l.productoId && !variantes ? 'Cargando...' : 'Selecciona una variante'}
                          </option>
                          {(variantes ?? []).map((v) => (
                            <option key={v.id} value={v.id}>
                              {v.nombre} (stock actual: {v.existencias})
                            </option>
                          ))}
                        </select>
                      </Campo>
                    </div>

                    <div className="CampoFila ComprasFila2">
                      <Campo
                        id={`campo-linea_${i}_cantidad`}
                        label="Cantidad"
                        obligatorio
                        error={errores[`linea_${i}_cantidad`]}
                      >
                        <input
                          id={`campo-linea_${i}_cantidad`}
                          className={clase(`linea_${i}_cantidad`)}
                          type="text"
                          inputMode="numeric"
                          value={l.cantidad}
                          onChange={(e) => cambiarLinea(i, 'cantidad', e.target.value)}
                          aria-invalid={Boolean(errores[`linea_${i}_cantidad`])}
                        />
                      </Campo>

                      <Campo
                        id={`campo-linea_${i}_costo`}
                        label="Costo por unidad (S/)"
                        obligatorio
                        error={errores[`linea_${i}_costo`]}
                      >
                        <input
                          id={`campo-linea_${i}_costo`}
                          className={clase(`linea_${i}_costo`)}
                          type="text"
                          inputMode="decimal"
                          placeholder="18.50"
                          value={l.costo}
                          onChange={(e) => cambiarLinea(i, 'costo', e.target.value)}
                          aria-invalid={Boolean(errores[`linea_${i}_costo`])}
                        />
                      </Campo>
                    </div>
                  </li>
                );
              })}
            </ul>

            <button type="button" className="FormBotonSecundario" onClick={agregarLinea}>
              + Agregar otro producto
            </button>

            <p className="ComprasTotal">
              Total de la compra: <strong>{soles(total)}</strong>
            </p>
          </fieldset>
        </fieldset>

        {/* ---- Archivo del comprobante (escenario 2) ---- */}
        <fieldset className="FormSeccion">
          <legend>Foto o PDF del comprobante</legend>
          <p className="CampoAyuda">
            JPG, PNG, WEBP o PDF, máximo {MAX_MB} MB.{' '}
            {COMPROBANTE_OBLIGATORIO ? 'Es obligatorio: respalda el ingreso de stock.' : 'Es opcional, pero respalda el ingreso de stock.'}
          </p>

          <input
            ref={archivoRef}
            id="campo-archivo"
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            className={`ComprasArchivo ${clase('archivo')}`}
            onChange={elegirArchivo}
          />
          {archivo && (
            <p className="ComprasArchivoNombre">
              {archivo.name} ({(archivo.size / 1024 / 1024).toFixed(2)} MB){' '}
              <button type="button" onClick={quitarArchivo}>Quitar</button>
            </p>
          )}
          {errores.archivo && <p className="CampoError" role="alert">{errores.archivo}</p>}
        </fieldset>

        {errorGeneral && (
          <div className="FormErrorGeneral" role="alert">
            <p>{errorGeneral}</p>
            {bloqueado && <Link to="/adminPanel/compras">Ir al listado de compras</Link>}
          </div>
        )}

        <div className="FormAcciones">
          <button type="submit" className="FormBotonPrimario" disabled={guardando}>
            {guardando
              ? 'Guardando...'
              : bloqueado
                ? 'Reintentar adjuntar comprobante'
                : 'Registrar compra'}
          </button>
          {!bloqueado && <Link to="/adminPanel/compras" className="FormCancelar">Cancelar</Link>}
        </div>
      </form>
    </AdminLayout>
  );
}

export default CompraForm;
