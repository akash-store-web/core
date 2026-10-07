import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import '../Login/Login.css';
import '../RecuperarContrasena/RecuperarContrasena.css';
import PassInput from '../Login/PassInput/PassInput.jsx';
import { restablecerContrasena } from '../../../services/recuperarService.js';
import logo from '../../../assets/logo.png';

const MIN_CARACTERES = 8;
const MAX_BYTES = 72; // límite de bcrypt en el backend

function validar(nueva, confirmacion) {
  if (nueva.length < MIN_CARACTERES) {
    return `La contraseña debe tener al menos ${MIN_CARACTERES} caracteres.`;
  }
  if (new TextEncoder().encode(nueva).length > MAX_BYTES) {
    return 'La contraseña es demasiado larga (máximo 72 bytes).';
  }
  if (nueva !== confirmacion) {
    return 'Las contraseñas no coinciden.';
  }
  return '';
}

function RestablecerContrasena() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [nueva, setNueva] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [exito, setExito] = useState('');
  const [enlaceInvalido, setEnlaceInvalido] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (loading) return;

    const problema = validar(nueva, confirmacion);
    if (problema) {
      setError(problema);
      return;
    }

    setError('');
    setLoading(true);

    try {
      const mensaje = await restablecerContrasena(token, nueva);
      setExito(mensaje);
    } catch (err) {
      // Escenario 3: enlace vencido, ya usado o inválido.
      if (err.enlaceInvalido) setEnlaceInvalido(true);
      else setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  let contenido;

  if (!token || enlaceInvalido) {
    contenido = (
      <>
        <h1 className="LoginTitle">Enlace no válido</h1>
        <p className="RecuperarMensaje" role="alert">
          El enlace no es válido o ya venció. Los enlaces duran un tiempo limitado y solo se
          pueden usar una vez.
        </p>
        <Link to="/recuperar" className="LoginButton RecuperarBoton">
          Solicitar un nuevo enlace
        </Link>
      </>
    );
  } else if (exito) {
    contenido = (
      <>
        <h1 className="LoginTitle">Contraseña actualizada</h1>
        <p className="RecuperarMensaje" role="status">{exito}</p>
        <Link to="/admin" className="LoginButton RecuperarBoton">
          Iniciar sesión
        </Link>
      </>
    );
  } else {
    contenido = (
      <>
        <h1 className="LoginTitle">Nueva contraseña</h1>
        <p className="LoginSubtitle">
          Elige una contraseña de al menos {MIN_CARACTERES} caracteres.
        </p>

        <form className="LoginForm" onSubmit={handleSubmit} noValidate>
          <PassInput
            placeholder="Nueva contraseña"
            value={nueva}
            onChange={(valor) => {
              setNueva(valor);
              setError('');
            }}
          />
          <PassInput
            placeholder="Confirmar contraseña"
            value={confirmacion}
            onChange={(valor) => {
              setConfirmacion(valor);
              setError('');
            }}
          />

          {error && <p className="LoginError" role="alert">{error}</p>}

          <button type="submit" className="LoginButton" disabled={loading}>
            {loading ? 'Guardando...' : 'Guardar contraseña'}
          </button>
          {loading && (
            <p className="RecuperarNota">
              Conectando con el servidor; la primera vez puede tardar hasta un minuto.
            </p>
          )}
          <Link to="/admin" className="LoginForgot">← Volver a iniciar sesión</Link>
        </form>
      </>
    );
  }

  return (
    <div className="LoginPage">
      <header className="LoginHeader">
        <img src={logo} alt="Logo Akash Store" />
        <span className="LoginHeaderName">Akash Store</span>
      </header>

      <main className="LoginMain">
        <section className="LoginCard">{contenido}</section>

        <aside className="LoginBrand">
          <img src={logo} alt="" className="LoginBrandLogo" />
          <h2 className="LoginBrandTitle">Akash Store</h2>
          <p className="LoginBrandText">
            Define una nueva contraseña para volver a tu panel de administración.
          </p>
        </aside>
      </main>
    </div>
  );
}

export default RestablecerContrasena;