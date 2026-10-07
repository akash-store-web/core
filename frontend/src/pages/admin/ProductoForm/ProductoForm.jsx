import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AdminLayout from '../../../components/AdminLayout.jsx';
import { crearProducto, listarCategorias } from '../../../services/productosService.js';
import './ProductoForm.css';

const MAX_FOTOS = 5;
const MAX_MB = 5;
const TIPOS_PERMITIDOS = ['image/jpeg', 'image/png', 'image/webp'];
// HU014 escenario 1 pide al menos una fotografía. Ponlo en false si el equipo decide lo contrario.
const FOTO_OBLIGATORIA = true;

const REGEX_DECIMAL = /^\d+(\.\d{1,2})?$/;
const REGEX_ENTERO = /^\d+$/;

const FORM_INICIAL = {
  nombre: '',
  categoria_id: '',
  descripcion: '',
  precio_base: '',
  material: '',
  medidas: '',
  peso_g: '',
  es_pieza_natural: false,
  existencias: '0',
  propiedades: '',
};

let contadorId = 0;
const nuevoId = () => ++contadorId;
const nuevaVariante = () => ({ key: nuevoId(), nombre: '', precio: '', existencias: '0', propiedades: '' });

const limpiarDecimal = (texto) => texto.trim().replace(',', '.');
const aTexto = (texto) => texto.trim() || null;
const aMonto = (texto) => {
  const limpio = limpiarDecimal(texto);
  return limpio ? Number(limpio).toFixed(2) : null;
};

function validar({ form, tieneVariantes, variantes, fotos }) {
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

  if (FOTO_OBLIGATORIA && fotos.length === 0) e.fotos = 'Sube al menos una fotografía.';

  if (tieneVariantes) {
    variantes.forEach((v, i) => {
      if (!v.nombre.trim()) e[`variante_${i}_nombre`] = 'Falta el nombre.';
      else if (v.nombre.trim().length > 80) e[`variante_${i}_nombre`] = 'Máximo 80 caracteres.';

      const precioVariante = limpiarDecimal(v.precio);
      if (precioVariante && (!REGEX_DECIMAL.test(precioVariante) || Number(precioVariante) <= 0)) {
        e[`variante_${i}_precio`] = 'Precio no válido.';
      }
      if (!REGEX_ENTERO.test(v.existencias.trim())) {
        e[`variante_${i}_existencias`] = 'Número entero, 0 o más.';
      }
    });
  } else if (!REGEX_ENTERO.test(form.existencias.trim())) {
    e.existencias = 'Ingresa un número entero, 0 o más.';
  }

  return e;
}

function construirDatos({ form, tieneVariantes, variantes }) {
  return {
    categoria_id: Number(form.categoria_id),
    nombre: form.nombre.trim(),
    descripcion: form.descripcion.trim(),
    precio_base: aMonto(form.precio_base),
    material: aTexto(form.material),
    medidas: aTexto(form.medidas),
    peso_g: aMonto(form.peso_g),
    es_pieza_natural: form.es_pieza_natural,
    existencias: Number(form.existencias.trim() || 0),
    propiedades: aTexto(form.propiedades),
    variantes: tieneVariantes
      ? variantes.map((v) => ({
          nombre: v.nombre.trim(),
          precio: aMonto(v.precio),
          existencias: Number(v.existencias.trim()),
          propiedades: aTexto(v.propiedades),
        }))
      : [],
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

function ProductoForm() {
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
      nuevas.push({ id: nuevoId(), file: archivo, url: URL.createObjectURL(archivo) });
    }

    if (nuevas.length > 0) setFotos((prev) => [...prev, ...nuevas]);
    setErrores((prev) => {
      const siguiente = { ...prev };
      if (mensaje) siguiente.fotos = mensaje;
      else delete siguiente.fotos;
      return siguiente;
    });
  }

  function quitarFoto(id) {
    const foto = fotos.find((f) => f.id === id);
    if (foto) URL.revokeObjectURL(foto.url);
    setFotos((prev) => prev.filter((f) => f.id !== id));
  }

  function hacerPrincipal(id) {
    setFotos((prev) => {
      const elegida = prev.find((f) => f.id === id);
      return elegida ? [elegida, ...prev.filter((f) => f.id !== id)] : prev;
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

  async function handleSubmit(e) {
    e.preventDefault();
    if (guardando) return;

    setErrorGeneral('');
    const encontrados = validar({ form, tieneVariantes, variantes, fotos });
    setErrores(encontrados);

    if (Object.keys(encontrados).length > 0) {
      // Escenario 2: se marca en rojo lo que falta y se conserva lo ya escrito.
      setTimeout(() => document.querySelector('.campo-invalido')?.focus(), 0);
      return;
    }

    setGuardando(true);
    try {
      await crearProducto(
        construirDatos({ form, tieneVariantes, variantes }),
        fotos.map((f) => f.file),
      );
      navigate('/adminPanel', { state: { creado: form.nombre.trim() } });
    } catch (err) {
      setErrorGeneral(err.message);
      if (err.productoId) setProductoParcialId(err.productoId);
      if (Array.isArray(err.detail)) aplicarErroresServidor(err.detail);
    } finally {
      setGuardando(false);
    }
  }

  const clase = (clave) => (errores[clave] ? 'campo-invalido' : '');

  return (
    <AdminLayout>
      <div className="FormCabecera">
        <Link to="/adminPanel" className="FormVolver">← Volver al listado</Link>
        <h1 className="FormTitulo">Nuevo producto</h1>
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
            De 1 a {MAX_FOTOS} fotos (JPG, PNG o WEBP, máximo {MAX_MB} MB cada una). La primera es
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
          <legend>Existencias y variantes</legend>

          <label className="CampoCheck">
            <input
              type="checkbox"
              checked={tieneVariantes}
              onChange={(e) => setTieneVariantes(e.target.checked)}
            />
            <span>Este producto tiene variantes (piedras, aromas, tamaños…)</span>
          </label>

          {!tieneVariantes ? (
            <Campo
              id="campo-existencias"
              label="Existencias"
              error={errores.existencias}
              ayuda="Un producto sin variantes se administra con una sola existencia."
            >
              <input
                id="campo-existencias"
                className={clase('existencias')}
                type="text"
                inputMode="numeric"
                value={form.existencias}
                onChange={(e) => cambiar('existencias', e.target.value)}
                aria-invalid={Boolean(errores.existencias)}
              />
            </Campo>
          ) : (
            <>
              <p className="CampoAyuda">
                Cada variante lleva sus propias existencias. Si dejas el precio vacío, usa el
                precio base.
              </p>
              <ul className="VariantesForm">
                {variantes.map((v, i) => (
                  <li key={v.key} className="VarianteForm">
                    <div className="VarianteFormTitulo">
                      <strong>Variante {i + 1}</strong>
                      {variantes.length > 1 && (
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

                      <Campo
                        id={`campo-variante_${i}_existencias`}
                        label="Existencias"
                        error={errores[`variante_${i}_existencias`]}
                      >
                        <input
                          id={`campo-variante_${i}_existencias`}
                          className={clase(`variante_${i}_existencias`)}
                          type="text"
                          inputMode="numeric"
                          value={v.existencias}
                          onChange={(e) => cambiarVariante(i, 'existencias', e.target.value)}
                          aria-invalid={Boolean(errores[`variante_${i}_existencias`])}
                        />
                      </Campo>
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
        <p className="FormNota">
          El producto se guardará como <strong>no publicado</strong>. Podrás publicarlo desde el
          listado cuando esté listo.
        </p>

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
            {guardando ? 'Guardando...' : 'Guardar producto'}
          </button>
          <Link to="/adminPanel" className="FormCancelar">Cancelar</Link>
        </div>
      </form>
    </AdminLayout>
  );
}

export default ProductoForm;