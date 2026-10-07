import { Link, NavLink, useNavigate } from 'react-router-dom';
import { logout } from '../services/authService.js';
import logo from '../assets/logo.png';
import './AdminLayout.css';

function AdminLayout({ children }) {
  const navigate = useNavigate();

  function cerrarSesion() {
    logout();
    navigate('/admin', { replace: true });
  }

  return (
    <div className="AdminPage">
      <header className="AdminHeader">
        <Link to="/adminPanel" className="AdminMarca">
          <img src={logo} alt="" />
          <span>Akash Store</span>
          <small>Panel</small>
        </Link>

        <nav className="AdminNav" aria-label="Secciones del panel">
          <NavLink to="/adminPanel" end>Productos</NavLink>
          <NavLink to="/adminPanel/envios">Envíos</NavLink>
        </nav>

        <button type="button" className="AdminSalir" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>
      <main className="AdminMain">{children}</main>
    </div>
  );
}

export default AdminLayout;