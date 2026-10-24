import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import {
  actualizarProducto,
  actualizarVariante,
  crearProducto,
  crearVariante,
  eliminarImagen,
  listarCategorias,
  listarVariantes,
  marcarImagenPrincipal,
  obtenerProducto,
  subirImagen,
} from '../../../services/productosService.js';
import './ProductoForm.css';

const MAX_FOTOS = 5;
const MAX_MB = 5;
const TIPOS_PERMITIDOS = ['image/jpeg', 'image/png', 'image/webp'];
// HU014 escenario 1 pide al menos una fotografía. Ponlo en false si el equipo decide lo contrario.
const FOTO_OBLIGATORIA = true;

const REGEX_DECIMAL = /^\d+(\.\d{1,2})?$/;

const FORM_INICIAL = {
  nombre: '',
  categoria_id: '',
  descripcion: '',
  precio_base: '',
  material: '',
  medidas: '',
  peso_g: '',
  es_pieza_natural: false,
  propiedades: '',
};

let contadorId = 0;
const nuevoId = () => ++contadorId;
// `id` = id en el backend (null mientras la variante es nueva). Las existencias NO se editan aquí.
const nuevaVariante = () => ({ key: nuevoId(), id: null, nombre: '', precio: '', propiedades: '' });
const NOMBRE_UNICA = 'Única';

const limpiarDecimal = (texto) => texto.trim().replace(',', '.');
const aTexto = (texto) => texto.trim() || null;
const aMonto = (texto) => {
  const limpio = limpiarDecimal(texto);
  return limpio ? Number(limpio).toFixed(2) : null;
};

function validar({ form, tieneVariantes, variantes, fotos, esEdicion }) {
  const e = {};

  if (!form.nombre.trim()) e.nombre = 'Ingresa el nombre del producto.';
  else if (form.nombre.trim().length > 120) e.nombre = 'Máximo 120 caracteres.';

  if (!form.categoria_id) e.categoria_id = 'Elige una categoría.';
  if (!form.descripcion.trim()) e.descripcion = 'Escribe una descripción.';

  const precio = limpiarDecimal(form.precio_base);
  if (!precio) e.precio_base = 'Ingresa el precio.';
  else if (!REGEX_DECIMAL.test(precio) || Number(precio) <= 0) {
    e.precio_base = 'Ingresa un precio mayor a 0, con hasta 2 decimales.';
  }

  if (form.material.trim().length > 80) e.material = 'Máximo 80 caracteres.';
  if (form.medidas.trim().length > 80) e.medidas = 'Máximo 80 caracteres.';

  const peso = limpiarDecimal(form.peso_g);
  if (peso && (!REGEX_DECIMAL.test(peso) || Number(peso) <= 0)) {
    e.peso_g = 'Ingresa un peso mayor a 0, con hasta 2 decimales.';
  }

  if (FOTO_OBLIGATORIA && !esEdicion && fotos.length === 0) e.fotos = 'Sube al menos una fotografía.';

  if (tieneVariantes) {
    variantes.forEach((v, i) => {
      if (!v.nombre.trim()) e[`variante_${i}_nombre`] = 'Falta el nombre.';
      else if (v.nombre.trim().length > 80) e[`variante_${i}_nombre`] = 'Máximo 80 caracteres.';

      const precioVariante = limpiarDecimal(v.precio);
      if (precioVariante && (!REGEX_DECIMAL.test(precioVariante) || Number(precioVariante) <= 0)) {
        e[`variante_${i}_precio`] = 'Precio no válido.';
      }
    });
  }

  return e;
}

// Datos del producto (sirve para crear con POST y para editar con PUT). Sin existencias.
function datosProducto(form) {
  return {
    categoria_id: Number(form.categoria_id),
    nombre: form.nombre.trim(),
    descripcion: form.descripcion.trim(),
    precio_base: aMonto(form.precio_base),
    material: aTexto(form.material),
    medidas: aTexto(form.medidas),
    peso_g: aMonto(form.peso_g),
    es_pieza_natural: form.es_pieza_natural,
  };
}

// Lo que viaja al backend por variante: nunca existencias (HU032 escenario 4).
const cuerpoVariante = (v) => ({
  nombre: v.nombre.trim(),
  precio: aMonto(v.precio),
  propiedades: aTexto(v.propiedades),
});

function construirDatos({ form, tieneVariantes, variantes }) {
  return {
    ...datosProducto(form),
    propiedades: aTexto(form.propiedades),
    variantes: tieneVariantes ? variantes.map(cuerpoVariante) : [],
  };
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

// Con HU034 el stock nunca se escribe en este formulario: entra por compras o ajustes con motivo.
// Al crear no hay nada que mostrar (todo nace con 0), solo el aviso; al editar se ve en solo lectura.
function ExistenciasNota({ esEdicion }) {
  return (
    <p className="ExistenciasAviso">
      {esEdicion
        ? 'Las existencias son solo de lectura: cambian al registrar una compra o un ajuste de inventario.'
        : 'El stock se carga registrando una compra.'}
    </p>
  );
}

// Producto sin variantes. Al editar muestra su única existencia sin permitir cambiarla.
function ExistenciasLectura({ esEdicion, existencias }) {
  if (!esEdicion) return <ExistenciasNota esEdicion={false} />;

  return (
    <div className="Campo">
      <span className="ExistenciasEtiqueta">Existencias</span>
      <p className="ExistenciasValor">
        {existencias ?? 0}
        <small> solo lectura</small>
      </p>
      <ExistenciasNota esEdicion />
    </div>
  );
}

// Convierte lo que devuelve el backend en lo que usa el formulario.
const aTextoForm = (valor) => (valor === null || valor === undefined ? '' : String(valor));

function ProductoForm() {
  const { id } = useParams();
  const esEdicion = Boolean(id);
  const navigate = useNavigate();
  const galeriaRef = useRef(null);
  const camaraRef = useRef(null);

  const [form, setForm] = useState(FORM_INICIAL);
  const [tieneVariantes, setTieneVariantes] = useState(false);
  const [variantes, setVariantes] = useState(() => [nuevaVariante()]);
  const [fotos, setFotos] = useState([]);
  const [errores, setErrores] = useState({});
  const [categorias, setCategorias] = useState([]);
  const [errorCategorias, setErrorCategorias] = useState('');
  const [errorGeneral, setErrorGeneral] = useState('');
  const [productoParcialId, setProductoParcialId] = useState(null);
  const [guardando, setGuardando] = useState(false);

  // Solo en edición (HU032)
  const [cargandoProducto, setCargandoProducto] = useState(esEdicion);
  const [errorCarga, setErrorCarga] = useState('');
  const [fotosQuitadas, setFotosQuitadas] = useState([]); // ids de imágenes ya guardadas que se borrarán al guardar
  const principalIdRef = useRef(null); // imagen que el backend tiene como principal
  const [unica, setUnica] = useState(null); // variante «Única» original, si el producto no tiene variantes
  const [conVariantesInicial, setConVariantesInicial] = useState(false);

  useEffect(() => {
    let activo = true;
    listarCategorias()
      .then((datos) => {
        if (activo) setCategorias(datos);
      })
      .catch((err) => {
        if (activo) setErrorCategorias(err.message);
      });
    return () => {
      activo = false;
    };
  }, []);

  // HU032 escenarios 1, 2 y 4: carga los datos actuales del producto en el mismo formulario.
  useEffect(() => {
    if (!esEdicion) return undefined;
    let activo = true;

    Promise.all([obtenerProducto(id), listarVariantes(Number(id))])
      .then(([producto, listaVariantes]) => {
        if (!activo) return;

        setForm({
          nombre: producto.nombre,
          categoria_id: String(producto.categoria_id),
          descripcion: producto.descripcion,
          precio_base: aTextoForm(producto.precio_base),
          material: aTextoForm(producto.material),
          medidas: aTextoForm(producto.medidas),
          peso_g: aTextoForm(producto.peso_g),
          es_pieza_natural: producto.es_pieza_natural,
          propiedades: '',
        });

        const cargadas = listaVariantes.map((v) => ({
          key: nuevoId(),
          id: v.id,
          nombre: v.nombre,
          precio: aTextoForm(v.precio),
          propiedades: aTextoForm(v.propiedades),
          existencias: v.existencias, // solo lectura
        }));
        const soloUnica = cargadas.length === 1 && cargadas[0].nombre === NOMBRE_UNICA;
        setConVariantesInicial(!soloUnica);
        setUnica(soloUnica ? cargadas[0] : null);
        setTieneVariantes(!soloUnica);
        setVariantes(cargadas);
        if (soloUnica) setForm((prev) => ({ ...prev, propiedades: cargadas[0].propiedades }));

        const ordenadas = [...(producto.imagenes ?? [])].sort(
          (a, b) => Number(b.es_principal) - Number(a.es_principal) || a.orden - b.orden,
        );
        principalIdRef.current = ordenadas.find((img) => img.es_principal)?.id ?? null;
        setFotos(ordenadas.map((img) => ({ id: nuevoId(), imagenId: img.id, url: img.url, file: null })));
      })
      .catch((err) => {
        if (activo) setErrorCarga(err.message);
      })
      .finally(() => {
        if (activo) setCargandoProducto(false);
      });

    return () => {
      activo = false;
    };
  }, [esEdicion, id]);

  function limpiarError(clave) {
    setErrores((prev) => {
      if (!prev[clave]) return prev;
      const siguiente = { ...prev };
      delete siguiente[clave];
      return siguiente;
    });
  }

  function cambiar(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    limpiarError(campo);
  }

  /* ---------- Variantes (HU027) ---------- */

  function cambiarVariante(indice, campo, valor) {
    setVariantes((prev) => prev.map((v, i) => (i === indice ? { ...v, [campo]: valor } : v)));
    limpiarError(`variante_${indice}_${campo}`);
  }

  // En edición, un producto con una sola variante «Única» puede pasar a tener variantes:
  // esa misma variante se renombra (no se pierde ni se duplica).
  function alternarVariantes(activo) {
    setTieneVariantes(activo);
    if (!esEdicion || !unica) return;

    if (activo) {
      setVariantes((prev) =>
        prev.map((v) => (v.id === unica.id ? { ...v, nombre: '', propiedades: form.propiedades } : v)),
      );
    } else {
      const actual = variantes.find((v) => v.id === unica.id);
      setForm((prev) => ({ ...prev, propiedades: actual?.propiedades ?? '' }));
      setVariantes((prev) => prev.map((v) => (v.id === unica.id ? { ...v, nombre: unica.nombre } : v)));
    }
  }

  function agregarVariante() {
    setVariantes((prev) => [...prev, nuevaVariante()]);
  }

  function quitarVariante(key) {
    setVariantes((prev) => prev.filter((v) => v.key !== key));
    // Los errores van por posición: al quitar una fila se recalculan al guardar.
    setErrores((prev) => {
      const siguiente = {};
      Object.keys(prev).forEach((clave) => {
        if (!clave.startsWith('variante_')) siguiente[clave] = prev[clave];
      });
      return siguiente;
    });
  }

  /* ---------- Fotografías (HU014 escenarios 3 y 4) ---------- */

  function agregarFotos(e) {
    const archivos = Array.from(e.target.files ?? []);
    e.target.value = ''; // permite volver a elegir la misma foto
    if (archivos.length === 0) return;

    const cupo = MAX_FOTOS - fotos.length;
    const nuevas = [];
    let mensaje = '';

    for (const archivo of archivos) {
      if (!TIPOS_PERMITIDOS.includes(archivo.type)) {
        mensaje = `«${archivo.name}»: usa una imagen JPG, PNG o WEBP.`;
        continue;
      }
      if (archivo.size > MAX_MB * 1024 * 1024) {
        mensaje = `«${archivo.name}» pesa más de ${MAX_MB} MB.`;
        continue;
      }
      if (nuevas.length >= cupo) {
        mensaje = `Máximo ${MAX_FOTOS} fotografías por producto.`;
        break;
      }
      nuevas.push({ id: nuevoId(), imagenId: null, file: archivo, url: URL.createObjectURL(archivo) });
    }

    if (nuevas.length > 0) setFotos((prev) => [...prev, ...nuevas]);
    setErrores((prev) => {
      const siguiente = { ...prev };
      if (mensaje) siguiente.fotos = mensaje;
      else delete siguiente.fotos;
      return siguiente;
    });
  }

  function quitarFoto(fotoId) {
    const foto = fotos.find((f) => f.id === fotoId);
    if (foto?.file) URL.revokeObjectURL(foto.url);
    // Una foto ya guardada no se borra hasta pulsar «Guardar cambios».
    if (foto?.imagenId) setFotosQuitadas((prev) => [...prev, foto.imagenId]);
    setFotos((prev) => prev.filter((f) => f.id !== fotoId));
  }

  function hacerPrincipal(fotoId) {
    setFotos((prev) => {
      const elegida = prev.find((f) => f.id === fotoId);
      return elegida ? [elegida, ...prev.filter((f) => f.id !== fotoId)] : prev;
    });
  }

  /* ---------- Guardar ---------- */

  function aplicarErroresServidor(detalle) {
    const porCampo = {};
    detalle.forEach((item) => {
      const campo = item.loc?.[1];
      if (typeof campo === 'string') porCampo[campo] = item.msg;
    });
    setErrores((prev) => ({ ...prev, ...porCampo }));
  }

  function aplicarErroresVariante(indice, detalle) {
    const porCampo = {};
    detalle.forEach((item) => {
      const campo = item.loc?.[1];
      if (typeof campo === 'string') porCampo[`variante_${indice}_${campo}`] = item.msg;
    });
    setErrores((prev) => ({ ...prev, ...porCampo }));
  }

  /*
    HU032: guarda los cambios paso a paso. Cada paso que termina bien queda reflejado en el
    estado (la variante recibe su id, la foto deja de ser «nueva»...), así que si algo falla a
    la mitad se puede volver a pulsar «Guardar cambios» sin duplicar nada.
  */
  async function guardarEdicion() {
    // 1. Datos del producto
    await actualizarProducto(Number(id), datosProducto(form));

    // 2. Variantes: se renombran/actualizan las existentes y se agregan las nuevas (sin tocar las demás)
    if (tieneVariantes) {
      const lista = [...variantes];
      for (let i = 0; i < lista.length; i += 1) {
        const v = lista[i];
        try {
          if (v.id) {
            await actualizarVariante(Number(id), v.id, cuerpoVariante(v));
          } else {
            const creada = await crearVariante(Number(id), cuerpoVariante(v));
            lista[i] = { ...v, id: creada.id, existencias: 0 };
            setVariantes((prev) => prev.map((x) => (x.key === v.key ? lista[i] : x)));
          }
        } catch (err) {
          if (Array.isArray(err.detail)) aplicarErroresVariante(i, err.detail);
          throw err;
        }
      }
    } else if (unica) {
      await actualizarVariante(Number(id), unica.id, {
        nombre: unica.nombre,
        precio: aMonto(unica.precio),
        propiedades: aTexto(form.propiedades),
      });
    }

    // 3. Fotos: primero se quitan, luego se suben las nuevas y al final se fija la principal
    for (const imagenId of [...fotosQuitadas]) {
      await eliminarImagen(Number(id), imagenId);
      if (principalIdRef.current === imagenId) principalIdRef.current = null;
      setFotosQuitadas((prev) => prev.filter((x) => x !== imagenId));
    }

    const lista = [...fotos];
    for (let i = 0; i < lista.length; i += 1) {
      const foto = lista[i];
      if (!foto.file) continue;
      const subida = await subirImagen(Number(id), foto.file);
      URL.revokeObjectURL(foto.url);
      lista[i] = { ...foto, imagenId: subida.id, url: subida.url, file: null };
      setFotos((prev) => prev.map((x) => (x.id === foto.id ? lista[i] : x)));
    }

    const deseada = lista[0]?.imagenId;
    if (deseada && deseada !== principalIdRef.current) {
      await marcarImagenPrincipal(Number(id), deseada);
      principalIdRef.current = deseada;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (guardando) return;

    setErrorGeneral('');
    const encontrados = validar({ form, tieneVariantes, variantes, fotos, esEdicion });
    setErrores(encontrados);

    if (Object.keys(encontrados).length > 0) {
      // Escenario 3: se marca en rojo lo que falta o está mal y se conserva lo ya escrito.
      setTimeout(() => document.querySelector('.campo-invalido')?.focus(), 0);
      return;
    }

    setGuardando(true);
    try {
      if (esEdicion) {
        await guardarEdicion();
        navigate('/adminPanel', { state: { editado: form.nombre.trim() } });
      } else {
        await crearProducto(
          construirDatos({ form, tieneVariantes, variantes }),
          fotos.map((f) => f.file),
        );
        navigate('/adminPanel', { state: { creado: form.nombre.trim() } });
      }
    } catch (err) {
      setErrorGeneral(
        esEdicion ? `No se pudieron guardar todos los cambios: ${err.message}` : err.message,
      );
      if (err.productoId) setProductoParcialId(err.productoId);
      if (Array.isArray(err.detail)) aplicarErroresServidor(err.detail);
    } finally {
      setGuardando(false);
    }
  }

  const clase = (clave) => (errores[clave] ? 'campo-invalido' : '');

  if (esEdicion && (cargandoProducto || errorCarga)) {
    return (
      <AdminLayout>
        <div className="FormCabecera">
          <Link to="/adminPanel" className="FormVolver">← Volver al listado</Link>
          <h1 className="FormTitulo">Editar producto</h1>
        </div>
        {cargandoProducto && <p className="CampoAyuda">Cargando producto...</p>}
        {errorCarga && <p className="FormErrorGeneral" role="alert">{errorCarga}</p>}
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="FormCabecera">
        <Link to="/adminPanel" className="FormVolver">← Volver al listado</Link>
        <h1 className="FormTitulo">{esEdicion ? 'Editar producto' : 'Nuevo producto'}</h1>
      </div>

      <form className="FormProducto" onSubmit={handleSubmit} noValidate>
        {/* ---- Datos del producto ---- */}
        <fieldset className="FormSeccion">
          <legend>Datos del producto</legend>

          <Campo id="campo-nombre" label="Nombre" obligatorio error={errores.nombre}>
            <input
              id="campo-nombre"
              className={clase('nombre')}
              type="text"
              maxLength={120}
              value={form.nombre}
              onChange={(e) => cambiar('nombre', e.target.value)}
              aria-invalid={Boolean(errores.nombre)}
            />
          </Campo>

          <Campo id="campo-categoria_id" label="Categoría" obligatorio error={errores.categoria_id}>
            <select
              id="campo-categoria_id"
              className={clase('categoria_id')}
              value={form.categoria_id}
              onChange={(e) => cambiar('categoria_id', e.target.value)}
              aria-invalid={Boolean(errores.categoria_id)}
            >
              <option value="">Selecciona una categoría</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
            {errorCategorias && <p className="CampoError">{errorCategorias}</p>}
          </Campo>

          <Campo id="campo-descripcion" label="Descripción" obligatorio error={errores.descripcion}>
            <textarea
              id="campo-descripcion"
              className={clase('descripcion')}
              rows={4}
              value={form.descripcion}
              onChange={(e) => cambiar('descripcion', e.target.value)}
              aria-invalid={Boolean(errores.descripcion)}
            />
          </Campo>

          <Campo
            id="campo-precio_base"
            label="Precio base (S/)"
            obligatorio
            error={errores.precio_base}
            ayuda="Es el precio que se muestra salvo que una variante tenga el suyo."
          >
            <input
              id="campo-precio_base"
              className={clase('precio_base')}
              type="text"
              inputMode="decimal"
              placeholder="25.00"
              value={form.precio_base}
              onChange={(e) => cambiar('precio_base', e.target.value)}
              aria-invalid={Boolean(errores.precio_base)}
            />
          </Campo>
        </fieldset>

        {/* ---- Atributos del rubro (escenario 5) ---- */}
        <fieldset className="FormSeccion">
          <legend>Atributos para la ficha pública</legend>

          <div className="CampoFila">
            <Campo id="campo-material" label="Material" error={errores.material}>
              <input
                id="campo-material"
                className={clase('material')}
                type="text"
                maxLength={80}
                placeholder="Plata 925"
                value={form.material}
                onChange={(e) => cambiar('material', e.target.value)}
                aria-invalid={Boolean(errores.material)}
              />
            </Campo>

            <Campo id="campo-medidas" label="Medidas" error={errores.medidas}>
              <input
                id="campo-medidas"
                className={clase('medidas')}
                type="text"
                maxLength={80}
                placeholder="Cuentas de 8 mm"
                value={form.medidas}
                onChange={(e) => cambiar('medidas', e.target.value)}
                aria-invalid={Boolean(errores.medidas)}
              />
            </Campo>

            <Campo id="campo-peso_g" label="Peso (g)" error={errores.peso_g}>
              <input
                id="campo-peso_g"
                className={clase('peso_g')}
                type="text"
                inputMode="decimal"
                placeholder="12.50"
                value={form.peso_g}
                onChange={(e) => cambiar('peso_g', e.target.value)}
                aria-invalid={Boolean(errores.peso_g)}
              />
            </Campo>
          </div>

          <label className="CampoCheck">
            <input
              type="checkbox"
              checked={form.es_pieza_natural}
              onChange={(e) => cambiar('es_pieza_natural', e.target.checked)}
            />
            <span>Es una pieza natural: puede verse distinta a la foto</span>
          </label>

          {!tieneVariantes && (
            <Campo
              id="campo-propiedades"
              label="Propiedades atribuidas"
              ayuda="Opcional. Por ejemplo: «Se le atribuye calma y armonía»."
            >
              <textarea
                id="campo-propiedades"
                rows={3}
                value={form.propiedades}
                onChange={(e) => cambiar('propiedades', e.target.value)}
              />
            </Campo>
          )}
        </fieldset>

        {/* ---- Fotografías ---- */}
        <fieldset className="FormSeccion">
          <legend>Fotografías</legend>
          <p className="CampoAyuda">
            {esEdicion ? 'Hasta' : 'De 1 a'} {MAX_FOTOS} fotos (JPG, PNG o WEBP, máximo {MAX_MB} MB cada una). La primera es
            la imagen principal del catálogo.
          </p>

          <input
            ref={galeriaRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            hidden
            onChange={agregarFotos}
          />
          <input
            ref={camaraRef}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={agregarFotos}
          />

          <div
            id="campo-fotos"
            className={`FotosAcciones ${clase('fotos')}`}
            tabIndex={-1}
          >
            <button
              type="button"
              className="FormBotonSecundario"
              disabled={fotos.length >= MAX_FOTOS}
              onClick={() => camaraRef.current?.click()}
            >
              Tomar foto
            </button>
            <button
              type="button"
              className="FormBotonSecundario"
              disabled={fotos.length >= MAX_FOTOS}
              onClick={() => galeriaRef.current?.click()}
            >
              Elegir de la galería
            </button>
            <span className="FotosContador">{fotos.length} de {MAX_FOTOS}</span>
          </div>
          {errores.fotos && <p className="CampoError" role="alert">{errores.fotos}</p>}

          {fotos.length > 0 && (
            <ul className="FotosLista">
              {fotos.map((foto, indice) => (
                <li key={foto.id} className="FotoItem">
                  <img src={foto.url} alt={`Foto ${indice + 1}`} />
                  {indice === 0 && <span className="FotoPrincipal">Principal</span>}
                  {foto.file && esEdicion && <span className="FotoNueva">Nueva</span>}
                  <div className="FotoBotones">
                    {indice !== 0 && (
                      <button type="button" onClick={() => hacerPrincipal(foto.id)}>
                        Hacer principal
                      </button>
                    )}
                    <button type="button" onClick={() => quitarFoto(foto.id)}>Quitar</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        {/* ---- Existencias y variantes (HU027) ---- */}
        <fieldset className="FormSeccion">
          <legend>Variantes</legend>

          <label className="CampoCheck">
            <input
              type="checkbox"
              checked={tieneVariantes}
              disabled={esEdicion && conVariantesInicial}
              onChange={(e) => alternarVariantes(e.target.checked)}
            />
            <span>Este producto tiene variantes (piedras, aromas, tamaños…)</span>
          </label>

          {!tieneVariantes ? (
            <ExistenciasLectura
              esEdicion={esEdicion}
              existencias={unica?.existencias}
            />
          ) : (
            <>
              <p className="CampoAyuda">
                Si dejas el precio de una variante vacío, usa el precio base.
              </p>
              <ExistenciasNota esEdicion={esEdicion} />
              <ul className="VariantesForm">
                {variantes.map((v, i) => (
                  <li key={v.key} className="VarianteForm">
                    <div className="VarianteFormTitulo">
                      <strong>Variante {i + 1}</strong>
                      {variantes.length > 1 && !v.id && (
                        <button type="button" onClick={() => quitarVariante(v.key)}>
                          Quitar
                        </button>
                      )}
                    </div>

                    <div className="CampoFila">
                      <Campo
                        id={`campo-variante_${i}_nombre`}
                        label="Nombre"
                        obligatorio
                        error={errores[`variante_${i}_nombre`]}
                      >
                        <input
                          id={`campo-variante_${i}_nombre`}
                          className={clase(`variante_${i}_nombre`)}
                          type="text"
                          maxLength={80}
                          placeholder="Amatista"
                          value={v.nombre}
                          onChange={(e) => cambiarVariante(i, 'nombre', e.target.value)}
                          aria-invalid={Boolean(errores[`variante_${i}_nombre`])}
                        />
                      </Campo>

                      <Campo
                        id={`campo-variante_${i}_precio`}
                        label="Precio propio (S/)"
                        error={errores[`variante_${i}_precio`]}
                      >
                        <input
                          id={`campo-variante_${i}_precio`}
                          className={clase(`variante_${i}_precio`)}
                          type="text"
                          inputMode="decimal"
                          placeholder="Opcional"
                          value={v.precio}
                          onChange={(e) => cambiarVariante(i, 'precio', e.target.value)}
                          aria-invalid={Boolean(errores[`variante_${i}_precio`])}
                        />
                      </Campo>

                      {/* Solo las variantes ya guardadas tienen existencias que mostrar */}
                      {v.id && (
                        <div className="Campo">
                          <span className="ExistenciasEtiqueta">Existencias</span>
                          <p className="ExistenciasValor" aria-label={`Existencias de ${v.nombre}`}>
                            {v.existencias}
                            <small> solo lectura</small>
                          </p>
                        </div>
                      )}
                    </div>

                    <Campo id={`campo-variante_${i}_propiedades`} label="Propiedades atribuidas">
                      <textarea
                        id={`campo-variante_${i}_propiedades`}
                        rows={2}
                        placeholder="Opcional"
                        value={v.propiedades}
                        onChange={(e) => cambiarVariante(i, 'propiedades', e.target.value)}
                      />
                    </Campo>
                  </li>
                ))}
              </ul>
              <button type="button" className="FormBotonSecundario" onClick={agregarVariante}>
                + Agregar variante
              </button>
            </>
          )}
        </fieldset>

        {/* ---- Guardar ---- */}
        {esEdicion ? (
          <p className="FormNota">
            Guardar no cambia si el producto está publicado ni sus existencias.
          </p>
        ) : (
          <p className="FormNota">
            El producto se guardará como <strong>no publicado</strong>. Podrás publicarlo desde el
            listado cuando esté listo.
          </p>
        )}

        {errorGeneral && (
          <div className="FormErrorGeneral" role="alert">
            <p>{errorGeneral}</p>
            {productoParcialId && (
              <Link to="/adminPanel">Ir al listado para revisarlo</Link>
            )}
          </div>
        )}

        <div className="FormAcciones">
          <button
            type="submit"
            className="FormBotonPrimario"
            disabled={guardando || Boolean(productoParcialId)}
          >
            {guardando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Guardar producto'}
          </button>
          <Link to="/adminPanel" className="FormCancelar">Cancelar</Link>
        </div>
      </form>
    </AdminLayout>
  );
}

export default ProductoForm;