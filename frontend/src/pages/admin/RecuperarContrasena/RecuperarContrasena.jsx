import { useState } from 'react';
import { Link } from 'react-router-dom';
import '../Login/Login.css';
import './RecuperarContrasena.css';
import EmailInput from '../Login/EmailInput/EmailInput.jsx';
import { validateEmail } from '../../../utils/validators.js';
import { solicitarRecuperacion } from '../../../services/recuperarService.js';
import logo from '../../../assets/logo.png';

function RecuperarContrasena() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();

    if (!validateEmail(email)) {
      setError('Ingresa un correo válido.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      // Se muestra el mismo mensaje exista o no el correo (escenario 2).
      const texto = await solicitarRecuperacion(email.trim().toLowerCase());
      setMensaje(texto);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="LoginPage">
      <header className="LoginHeader">
        <img src={logo} alt="Logo Akash Store" />
        <span className="LoginHeaderName">Akash Store</span>
      </header>

      <main className="LoginMain">
        <section className="LoginCard">
          {mensaje ? (
            <>
              <h1 className="LoginTitle">Revisa tu correo</h1>
              <p className="RecuperarMensaje" role="status">{mensaje}</p>
              <p className="RecuperarNota">
                El enlace tiene una vigencia limitada. Si no lo recibes, revisa
                tu carpeta de spam o solicita uno nuevo.
              </p>
              <Link to="/admin" className="LoginButton RecuperarBoton">
                Volver a iniciar sesión
              </Link>
            </>
          ) : (
            <>
              <h1 className="LoginTitle">Recuperar acceso</h1>
              <p className="LoginSubtitle">
                Ingresa el correo de tu cuenta y te enviaremos un enlace para
                restablecer tu contraseña.
              </p>

              <form className="LoginForm" onSubmit={handleSubmit} noValidate>
                <EmailInput
                  placeholder="Correo electrónico"
                  value={email}
                  onChange={setEmail}
                />

                {error && <p className="LoginError" role="alert">{error}</p>}

                <button type="submit" className="LoginButton" disabled={loading}>
                  {loading ? 'Enviando...' : 'Enviar enlace'}
                </button>
                <Link to="/admin" className="LoginForgot">
                  ← Volver a iniciar sesión
                </Link>
              </form>
            </>
          )}
        </section>

        <aside className="LoginBrand">
          <img src={logo} alt="" className="LoginBrandLogo" />
          <h2 className="LoginBrandTitle">Akash Store</h2>
          <p className="LoginBrandText">
            Recupera el acceso a tu panel de administración en pocos pasos.
          </p>
        </aside>
      </main>
    </div>
  );
}

export default RecuperarContrasena;