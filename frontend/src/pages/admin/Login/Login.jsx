import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Login.css';
import EmailInput from './EmailInput/EmailInput.jsx';
import PassInput from './PassInput/PassInput.jsx';
import { validateEmail } from '../../../utils/validators.js';
import { login } from '../../../services/authService.js';
import logo from '../../../assets/logo.png';

function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (loading) return;

    if (!validateEmail(email) || !password) {
      setError('Ingresa un correo válido y tu contraseña.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      await login(email.trim().toLowerCase(), password);
      navigate('/adminPanel', { replace: true });
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
          <h1 className="LoginTitle">Inicia sesión</h1>
          <p className="LoginSubtitle">Panel de administración</p>

          <form className="LoginForm" onSubmit={handleSubmit} noValidate>
            <EmailInput
              placeholder="Correo electrónico"
              value={email}
              onChange={setEmail}
            />
            <PassInput
              placeholder="Contraseña"
              value={password}
              onChange={setPassword}
            />

            {error && <p className="LoginError" role="alert">{error}</p>}

            <button type="submit" className="LoginButton" disabled={loading}>
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
            <Link to="/recuperar" className="LoginForgot">¿Olvidaste tu contraseña?</Link>
          </form>
        </section>

        <aside className="LoginBrand">
          <img src={logo} alt="" className="LoginBrandLogo" />
          <h2 className="LoginBrandTitle">Akash Store</h2>
          <p className="LoginBrandText">
            Administra tus productos, precios y pedidos desde un solo lugar.
          </p>
        </aside>
      </main>
    </div>
  );
}

export default Login;