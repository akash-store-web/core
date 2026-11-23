import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import AvisoPiezaNatural from '../../components/Carrito/AvisoPiezaNatural.jsx';
import { useCarrito } from '../../context/carritoContext.js';
import { aplicarRevision, cambiarCantidad, obtenerCarrito, quitarDelCarrito, vaciarCarrito, validarCarrito } from '../../services/carritoService.js';
import { PLACEHOLDER } from '../../services/catalogoService.js';
import { WHATSAPP_NUMBER } from '../../services/config.js';
import { listarDistritosEnvio } from '../../services/envioService.js';
import { guardarUltimoPedido, leerUltimoPedido, registrarPedido } from '../../services/pedidosService.js';
import { aCentimos, avisoPiezaNatural, combinarConRevision, resumirCarrito } from '../../utils/carrito.js';
import { soles } from '../../utils/formato.js';
import {
  APELLIDO_MAX,
  DIRECCION_MAX,
  NOMBRES_MAX,
  REFERENCIA_MAX,
  armarCuerpoPedido,
  costoEnvioEstimado,
  validarDatosPedido,
} from '../../utils/pedido.js';
import { armarMensajePedido, enlaceWhatsApp } from '../../utils/whatsapp.js';
import './Pedido.css';

// Orden en que se revisan los campos: el foco va al primero que tenga error (E4).
const CAMPOS = ['nombres', 'apellido_paterno', 'apellido_materno', 'celular', 'distrito', 'direccion', 'referencia'];
const DATOS_INICIALES = {
  nombres: '',
  apellido_paterno: '',
  apellido_materno: '',
  celular: '',
  distritoId: '',
  direccion: '',
  referencia: '',
};

const indexar = (items = []) => Object.fromEntries(items.map((item) => [item.variante_id, item]));
const firmaDe = (items) => items.map((i) => `${i.variante_id}:${i.cantidad}`).join(',');

/*
  WhatsApp se abre en una pestaña nueva. Los navegadores solo permiten abrir ventanas en el mismo
  instante del clic; después de esperar al servidor, window.open queda bloqueado. Por eso la
  pestaña se abre al pulsar el botón (con un texto de espera) y, cuando el pedido se registra,
  se la manda a WhatsApp. Si el navegador la bloquea igual, queda el botón de la confirmación (E8).
*/
function abrirPestanaDeEspera() {
  const pestana = window.open('', '_blank');
  if (!pestana) return null;
  try {
    pestana.opener = null; // la pestaña nueva no puede controlar la tienda
    pestana.document.title = 'Abriendo WhatsApp…';
    pestana.document.body.innerHTML =
      '<p style="font-family: system-ui, sans-serif; padding: 24px; color: #5E4028">Registrando tu pedido y abriendo WhatsApp…</p>';
  } catch {
    // Si no se puede escribir en ella, igual sirve para redirigirla.
  }
  return pestana;
}

// Ruta /pedido (HU010)
function PedidoPage() {
  const { items } = useCarrito();
  const [confirmado, setConfirmado] = useState(null); // { pedido, enlace, whatsappAbierto }
  const [ultimo] = useState(leerUltimoPedido); // Esc. 3: si vuelve con el carrito vacío, ve su número

  if (confirmado) return <Confirmacion {...confirmado} />;
  if (items.length > 0) return <FormularioPedido onConfirmado={setConfirmado} />;
  if (ultimo) return <Confirmacion {...ultimo} desdeAntes />;

  return (
    <div className="Pedido__vacio">
      <title>Tu pedido | Akash Store Perú</title>
      <h1 className="PublicTitulo">Tu carrito está vacío</h1>
      <p className="PublicBajada">Agrega productos desde el catálogo para armar tu pedido.</p>
      <Link to="/catalogo" className="Pedido__boton">
        Ver el catálogo
      </Link>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Formulario + resumen                                               */
/* ------------------------------------------------------------------ */

function FormularioPedido({ onConfirmado }) {
  const { items, abrir: abrirCarrito } = useCarrito();
  const formularioRef = useRef(null);
  const avisoRef = useRef(null);
  const enviandoRef = useRef(false); // E9: corta el segundo clic aunque React aún no haya repintado

  const [datos, setDatos] = useState(DATOS_INICIALES);
  const [intentoEnvio, setIntentoEnvio] = useState(false); // los errores se muestran tras el primer intento
  const [errorServidor, setErrorServidor] = useState(null); // { campo, texto } (422 del backend)
  const [aviso, setAviso] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const [distritos, setDistritos] = useState({ fase: 'cargando', lista: [] });
  const [intentoDistritos, setIntentoDistritos] = useState(0);

  // Revisión del carrito con el servidor. `firma` dice para qué contenido es la revisión:
  // si el carrito cambió (por ejemplo, desde el panel), se vuelve a revisar sola.
  const [revision, setRevision] = useState({ firma: null, porVariante: {}, avisoTexto: null, error: false });
  const [intentoRevision, setIntentoRevision] = useState(0);
  const firma = firmaDe(items);

  useEffect(() => {
    const controller = new AbortController();
    listarDistritosEnvio({ signal: controller.signal })
      .then((lista) => {
        if (!controller.signal.aborted) setDistritos({ fase: 'lista', lista });
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        console.error('Distritos:', error);
        setDistritos({ fase: 'error', lista: [] });
      });
    return () => controller.abort();
  }, [intentoDistritos]);

  useEffect(() => {
    const porRevisar = obtenerCarrito();
    if (porRevisar.length === 0) return undefined;
    const controller = new AbortController();
    validarCarrito(porRevisar, { signal: controller.signal })
      .then((respuesta) => {
        if (controller.signal.aborted) return;
        aplicarRevision(respuesta); // E7: el precio guardado pasa a ser el del servidor
        setRevision({
          firma: firmaDe(porRevisar),
          porVariante: indexar(respuesta.items),
          avisoTexto: respuesta.aviso_pieza_natural?.texto ?? null, // HU006
          error: false,
        });
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        console.error('Revisar carrito:', error);
        setRevision((previa) => ({ ...previa, firma: firmaDe(porRevisar), error: true }));
      });
    return () => controller.abort();
  }, [firma, intentoRevision]);

  const revisando = revision.firma !== firma;
  const lineas = combinarConRevision(items, revision.porVariante);
  const resumen = resumirCarrito(lineas);
  const avisoNatural = avisoPiezaNatural(lineas, revision.avisoTexto); // HU006 Esc. 2: antes de confirmar
  const distrito = distritos.lista.find((d) => d.id === Number(datos.distritoId));
  const envio = costoEnvioEstimado(distrito);
  const totalCentimos = resumen.totalCentimos + aCentimos(envio);

  // E4 / E5: los errores se calculan a partir de los datos (no se copian a otro estado)
  const errores = intentoEnvio ? validarDatosPedido(datos, distritos.lista) : {};
  if (errorServidor && !errores[errorServidor.campo]) errores[errorServidor.campo] = errorServidor.texto;

  function cambiar(evento) {
    const { name, value } = evento.target;
    const campo = name === 'distrito' ? 'distritoId' : name;
    setDatos((previos) => ({ ...previos, [campo]: value }));
    if (errorServidor?.campo === name) setErrorServidor(null);
  }

  function reintentarRevision() {
    setRevision((previa) => ({ ...previa, firma: null, error: false }));
    setIntentoRevision((n) => n + 1);
  }

  function reintentarDistritos() {
    setDistritos({ fase: 'cargando', lista: [] });
    setIntentoDistritos((n) => n + 1);
  }

  function mostrarAviso(texto) {
    setAviso(texto);
    // El foco va al aviso para que se lea (y no se pierda si el botón estaba deshabilitado)
    requestAnimationFrame(() => avisoRef.current?.focus());
  }

  async function enviar(evento) {
    evento.preventDefault();
    if (enviandoRef.current) return; // E9

    setIntentoEnvio(true);
    setAviso(null);

    const nuevosErrores = validarDatosPedido(datos, distritos.lista);
    const primero = CAMPOS.find((campo) => nuevosErrores[campo]);
    if (primero) {
      formularioRef.current?.querySelector(`[name="${primero}"]`)?.focus(); // E4: no se registra
      return;
    }
    if (!WHATSAPP_NUMBER) {
      mostrarAviso('Por ahora no podemos abrir WhatsApp desde la tienda. Inténtalo más tarde.');
      return;
    }
    if (revisando) {
      mostrarAviso('Un momento: estamos confirmando precios y disponibilidad. Vuelve a pulsar el botón en unos segundos.');
      return;
    }
    if (!resumen.puedeContinuar) {
      mostrarAviso('Quita o ajusta los productos marcados en tu pedido antes de enviarlo.');
      return;
    }

    enviandoRef.current = true;
    setEnviando(true);
    const pestana = abrirPestanaDeEspera();

    try {
      const pedido = await registrarPedido(armarCuerpoPedido(datos, obtenerCarrito()));
      const enlace = enlaceWhatsApp(WHATSAPP_NUMBER, armarMensajePedido(pedido));

      guardarUltimoPedido(pedido, enlace);
      try {
        vaciarCarrito(); // Esc. 3
      } catch (error) {
        console.error('Vaciar carrito:', error); // el pedido ya está registrado: se sigue igual
      }

      let whatsappAbierto = false;
      if (pestana && !pestana.closed) {
        pestana.location.href = enlace; // Esc. 1 y 2: app en el celular, WhatsApp Web en la computadora
        whatsappAbierto = true;
      }
      onConfirmado({ pedido, enlace, whatsappAbierto });
    } catch (error) {
      pestana?.close();

      if (error.status === 409 && Array.isArray(error.detail?.items)) {
        // E6: se marcan las líneas que fallaron y no se registra nada
        setRevision((previa) => {
          const porVariante = { ...previa.porVariante };
          for (const item of error.detail.items) {
            porVariante[item.variante_id] = { ...porVariante[item.variante_id], ...item };
          }
          return { ...previa, porVariante };
        });
        mostrarAviso('Algunos productos se agotaron mientras completabas tus datos. Quítalos o ajusta la cantidad y vuelve a enviar.');
      } else if (error.status === 422) {
        const texto = typeof error.detail === 'string' ? error.detail : 'Revisa los datos del formulario.';
        if (/distrito/i.test(texto)) setErrorServidor({ campo: 'distrito', texto });
        mostrarAviso(texto);
      } else {
        console.error('Registrar pedido:', error);
        mostrarAviso('No pudimos registrar tu pedido. Revisa tu conexión e inténtalo de nuevo; no se envió nada.');
      }
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  async function ajustar(linea) {
    try {
      await cambiarCantidad(linea.variante_id, linea.cantidadMaxima); // bajar: no necesita servidor
    } catch (error) {
      console.error('Ajustar cantidad:', error);
    }
  }

  function quitar(linea) {
    try {
      quitarDelCarrito(linea.variante_id);
    } catch (error) {
      mostrarAviso(error.message);
    }
  }

  // Props comunes de cada campo: valor, error accesible y id del mensaje
  const propsCampo = (nombre, valor) => ({
    id: `pedido-${nombre}`,
    name: nombre,
    value: valor,
    onChange: cambiar,
    'aria-invalid': errores[nombre] ? true : undefined,
    'aria-describedby': errores[nombre] ? `pedido-${nombre}-error` : undefined,
    className: `Pedido__control ${errores[nombre] ? 'campo-invalido' : ''}`,
  });

  // Mensaje de error de un campo (es una función que devuelve JSX, no un componente:
  // declarar componentes dentro de otro hace que React los vuelva a crear en cada render)
  const mensajeError = (campo) =>
    errores[campo] ? (
      <p id={`pedido-${campo}-error`} className="CampoError" role="alert">
        {errores[campo]}
      </p>
    ) : null;

  return (
    <div className="Pedido">
      <title>Enviar pedido | Akash Store Perú</title>
      <h1 className="PublicTitulo">Tu pedido</h1>
      <p className="PublicBajada">
        Completa tus datos y te abrimos WhatsApp con el pedido ya escrito. El pago y la entrega se
        coordinan por ahí con la tienda.
      </p>

      <form ref={formularioRef} className="Pedido__cuerpo" onSubmit={enviar} noValidate>
        <div className="Pedido__datos">
          <fieldset className="Pedido__grupo">
            <legend className="Pedido__subtitulo">Tus datos</legend>

            <div className="Pedido__campo">
              <label htmlFor="pedido-nombres">Nombres</label>
              <input
                {...propsCampo('nombres', datos.nombres)}
                type="text"
                autoComplete="given-name"
                autoCapitalize="words"
                maxLength={NOMBRES_MAX}
              />
              {mensajeError('nombres')}
            </div>

            <div className="Pedido__fila">
              <div className="Pedido__campo">
                <label htmlFor="pedido-apellido_paterno">Apellido paterno</label>
                <input
                  {...propsCampo('apellido_paterno', datos.apellido_paterno)}
                  type="text"
                  autoComplete="family-name"
                  autoCapitalize="words"
                  maxLength={APELLIDO_MAX}
                />
                {mensajeError('apellido_paterno')}
              </div>
              <div className="Pedido__campo">
                <label htmlFor="pedido-apellido_materno">Apellido materno</label>
                <input
                  {...propsCampo('apellido_materno', datos.apellido_materno)}
                  type="text"
                  autoComplete="off"
                  autoCapitalize="words"
                  maxLength={APELLIDO_MAX}
                />
                {mensajeError('apellido_materno')}
              </div>
            </div>

            <div className="Pedido__campo">
              <label htmlFor="pedido-celular">Celular</label>
              <input
                {...propsCampo('celular', datos.celular)}
                type="tel"
                inputMode="tel"
                autoComplete="tel-national"
                maxLength={15}
                aria-describedby={`pedido-celular-ayuda${errores.celular ? ' pedido-celular-error' : ''}`}
              />
              <p id="pedido-celular-ayuda" className="Pedido__ayuda">9 dígitos, empieza con 9. Ejemplo: 987 654 321</p>
              {mensajeError('celular')}
            </div>
          </fieldset>

          <fieldset className="Pedido__grupo">
            <legend className="Pedido__subtitulo">Entrega a domicilio</legend>
            <p className="Pedido__ayuda">
              Te lo llevamos a tu dirección. El costo de envío depende de tu distrito.
            </p>

            <div className="Pedido__campo">
              <label htmlFor="pedido-distrito">Distrito</label>
              {distritos.fase === 'error' ? (
                <div className="Pedido__aviso Pedido__aviso--error" role="alert">
                  <p>No pudimos cargar los distritos.</p>
                  <button type="button" className="Pedido__secundario" onClick={reintentarDistritos}>
                    Reintentar
                  </button>
                </div>
              ) : (
                <select {...propsCampo('distrito', datos.distritoId)} disabled={distritos.fase === 'cargando'}>
                  <option value="">{distritos.fase === 'cargando' ? 'Cargando distritos…' : 'Elige tu distrito'}</option>
                  {distritos.lista.map((d) => {
                    const sinDelivery = !d.con_cobertura;
                    return (
                      <option key={d.id} value={d.id} disabled={sinDelivery}>
                        {d.nombre}
                        {sinDelivery ? ' (sin delivery)' : ''}
                      </option>
                    );
                  })}
                </select>
              )}
              {envio != null && distrito && (
                <p className="Pedido__ayuda">Envío a {distrito.nombre}: {soles(envio)}</p>
              )}
              {mensajeError('distrito')}
            </div>

            <div className="Pedido__campo">
              <label htmlFor="pedido-direccion">Dirección</label>
              <input
                {...propsCampo('direccion', datos.direccion)}
                type="text"
                autoComplete="street-address"
                maxLength={DIRECCION_MAX}
                aria-describedby={`pedido-direccion-ayuda${errores.direccion ? ' pedido-direccion-error' : ''}`}
              />
              <p id="pedido-direccion-ayuda" className="Pedido__ayuda">Calle, número y, si tiene, dpto. Ejemplo: Av. Larco 345, dpto. 502</p>
              {mensajeError('direccion')}
            </div>
            <div className="Pedido__campo">
              <label htmlFor="pedido-referencia">
                Referencia <span className="Pedido__opcional">(opcional)</span>
              </label>
              <input {...propsCampo('referencia', datos.referencia)} type="text" maxLength={REFERENCIA_MAX} />
              {mensajeError('referencia')}
            </div>
          </fieldset>
        </div>

        <aside className="Pedido__resumen" aria-labelledby="pedido-resumen-titulo">
          <div className="Pedido__resumenCabecera">
            <h2 id="pedido-resumen-titulo" className="Pedido__subtitulo">Resumen</h2>
            <button type="button" className="Pedido__enlace" onClick={abrirCarrito}>
              Editar carrito
            </button>
          </div>

          {revisando && !revision.error && (
            <p className="Pedido__aviso" role="status">Confirmando precios y disponibilidad…</p>
          )}
          {revision.error && !revisando && (
            <div className="Pedido__aviso Pedido__aviso--error" role="alert">
              <p>No pudimos confirmar precios y disponibilidad.</p>
              <button type="button" className="Pedido__secundario" onClick={reintentarRevision}>
                Reintentar
              </button>
            </div>
          )}

          <ul className="Pedido__lineas">
            {lineas.map((linea) => {
              const fuera = !linea.cuenta;
              const porAjustar = linea.estado === 'stock_insuficiente' || linea.estado === 'limite';
              return (
                <li key={linea.variante_id} className={`Pedido__linea ${fuera ? 'Pedido__linea--fuera' : ''}`}>
                  <img src={linea.foto || PLACEHOLDER} alt="" width="48" height="48" className="Pedido__foto" />
                  <div className="Pedido__lineaInfo">
                    <p className="Pedido__lineaNombre">{linea.producto}</p>
                    <p className="Pedido__lineaDetalle">
                      {linea.variante ? `${linea.variante} · ` : ''}× {linea.cantidad}
                    </p>
                    {fuera && (
                      <p className="Pedido__lineaError">
                        {linea.estado === 'agotado' ? 'Agotado.' : 'Ya no está disponible.'}{' '}
                        <button type="button" className="Pedido__enlace" onClick={() => quitar(linea)}>
                          Quitar
                        </button>
                      </p>
                    )}
                    {porAjustar && (
                      <p className="Pedido__lineaError">
                        Solo hay {linea.cantidadMaxima}.{' '}
                        {linea.cantidadMaxima > 0 && (
                          <button type="button" className="Pedido__enlace" onClick={() => ajustar(linea)}>
                            Dejar {linea.cantidadMaxima}
                          </button>
                        )}
                      </p>
                    )}
                    {linea.precioCambio && linea.precioAnterior != null && (
                      <p className="Pedido__lineaInfoPrecio">
                        Precio actualizado: antes {soles(linea.precioAnterior)}.
                      </p>
                    )}
                  </div>
                  <p className="Pedido__lineaPrecio">{fuera ? 'No suma' : soles(linea.subtotalCentimos / 100)}</p>
                </li>
              );
            })}
          </ul>

          <dl className="Pedido__totales">
            <div>
              <dt>Productos</dt>
              <dd>{soles(resumen.totalCentimos / 100)}</dd>
            </div>
            <div>
              <dt>Envío</dt>
              <dd>
{envio != null ? soles(envio) : 'Elige tu distrito'}
              </dd>
            </div>
            <div className="Pedido__total" aria-live="polite">
              <dt>Total</dt>
              <dd>{soles(totalCentimos / 100)}</dd>
            </div>
          </dl>

          <AvisoPiezaNatural aviso={avisoNatural} />

          {aviso && (
            <p ref={avisoRef} className="Pedido__aviso Pedido__aviso--error" role="alert" tabIndex={-1}>
              {aviso}
            </p>
          )}

          <button type="submit" className="Pedido__boton" disabled={enviando} aria-busy={enviando || undefined}>
            {enviando ? 'Registrando tu pedido…' : 'Enviar pedido por WhatsApp'}
          </button>
          <p className="Pedido__ayuda Pedido__ayuda--centro">
            Aún no pagas nada: el pago y la entrega se coordinan por WhatsApp.
          </p>
        </aside>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Confirmación (Esc. 1, Esc. 3 y E8)                                 */
/* ------------------------------------------------------------------ */

function Confirmacion({ pedido, enlace, whatsappAbierto = false, desdeAntes = false }) {
  const tituloRef = useRef(null);

  // Al aparecer la confirmación: arriba de la página y el foco en el título (lo lee el lector de pantalla)
  useEffect(() => {
    window.scrollTo(0, 0);
    tituloRef.current?.focus();
  }, []);

  let texto = 'No pudimos abrir WhatsApp automáticamente. Usa el botón para enviar tu pedido a la tienda.';
  if (desdeAntes) texto = 'Este es tu último pedido. Si aún no enviaste el mensaje por WhatsApp, puedes abrirlo aquí.';
  else if (whatsappAbierto) texto = 'Abrimos WhatsApp con tu pedido en otra pestaña. Envía el mensaje para coordinar el pago y la entrega.';

  return (
    <section className="Pedido Pedido--confirmado" aria-labelledby="pedido-confirmado-titulo">
      <title>{`Pedido ${pedido.numero} | Akash Store Perú`}</title>
      <p className="Pedido__check" aria-hidden="true">✓</p>
      <h1 id="pedido-confirmado-titulo" ref={tituloRef} tabIndex={-1} className="PublicTitulo">
        Pedido {pedido.numero} registrado
      </h1>
      {pedido.repetido && (
        <p className="Pedido__ayuda">Este pedido ya estaba registrado, así que no se creó otro.</p>
      )}
      <p className="PublicBajada">{texto}</p>

      {/* E8: enlace normal (no JavaScript): el navegador no lo bloquea */}
      <a className="Pedido__boton Pedido__boton--whatsapp" href={enlace} target="_blank" rel="noopener noreferrer">
        {whatsappAbierto || desdeAntes ? 'Abrir WhatsApp de nuevo' : 'Abrir WhatsApp'}
      </a>

      <div className="Pedido__resumen Pedido__resumen--confirmado">
        <h2 className="Pedido__subtitulo">Detalle</h2>
        <ul className="Pedido__lineas">
          {pedido.items.map((item) => (
            <li key={item.variante_id} className="Pedido__linea Pedido__linea--simple">
              <div className="Pedido__lineaInfo">
                <p className="Pedido__lineaNombre">{item.producto}</p>
                <p className="Pedido__lineaDetalle">
                  {item.variante && item.variante !== 'Única' ? `${item.variante} · ` : ''}× {item.cantidad}
                </p>
              </div>
              <p className="Pedido__lineaPrecio">{soles(item.subtotal)}</p>
            </li>
          ))}
        </ul>
        <dl className="Pedido__totales">
          <div>
            <dt>Productos</dt>
            <dd>{soles(pedido.subtotal)}</dd>
          </div>
          {/* «Recojo» solo puede salir en un último pedido guardado antes de AKASH-196 */}
          <div>
            <dt>{pedido.modalidad_entrega === 'delivery' ? `Envío a ${pedido.distrito}` : 'Recojo'}</dt>
            <dd>{pedido.modalidad_entrega === 'delivery' ? soles(pedido.costo_envio) : 'Sin costo'}</dd>
          </div>
          <div className="Pedido__total">
            <dt>Total</dt>
            <dd>{soles(pedido.total)}</dd>
          </div>
        </dl>
      </div>

      <p className="Pedido__ayuda">
        La tienda te confirmará la disponibilidad, el pago y la entrega por WhatsApp.
      </p>
      <Link to="/catalogo" className="Pedido__secundario">
        Seguir viendo el catálogo
      </Link>
    </section>
  );
}

export default PedidoPage;
