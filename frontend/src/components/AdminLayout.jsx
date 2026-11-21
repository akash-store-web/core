import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../services/authService.js';
import { contarPedidosPendientes } from '../services/pedidosAdminService.js';
import logo from '../assets/logo.png';
import './AdminLayout.css';

/*
  Estructura del panel (HU017): barra lateral fija en computadora (≥ 1024px) y menú que se
  abre con ☰ en celular y tablet. Para agregar una sección nueva (por ejemplo «Ventas del mes»
  o «Clientas frecuentes» en el próximo sprint), basta con sumarla aquí.
*/
const SECCIONES = [
  {
    titulo: 'Tienda',
    enlaces: [
      { to: '/adminPanel', texto: 'Productos', icono: 'productos', activoSi: (ruta) => ruta === '/adminPanel' || ruta.startsWith('/adminPanel/productos') },
      { to: '/adminPanel/pedidos', texto: 'Pedidos', icono: 'pedidos', conContador: true },
      { to: '/adminPanel/ventas', texto: 'Ventas del mes', icono: 'ventas' },
    ],
  },
  {
    titulo: 'Inventario',
    enlaces: [{ to: '/adminPanel/compras', texto: 'Compras', icono: 'compras' }],
  },
  {
    titulo: 'Configuración',
    enlaces: [{ to: '/adminPanel/envios', texto: 'Envíos', icono: 'envios' }],
  },
];

const ICONOS = {
  productos: 'M4 7l8-4 8 4-8 4-8-4Z M4 7v10l8 4 8-4V7 M12 11v10',
  pedidos: 'M6 3h12v18l-3-2-3 2-3-2-3 2V3Z M9 8h6 M9 12h6',
  compras: 'M3 4h3l2 11h11l2-8H7 M10 20a1 1 0 1 0 0-.01 M17 20a1 1 0 1 0 0-.01',
  envios: 'M3 7h11v9H3Z M14 10h4l3 3v3h-7 M7 19a2 2 0 1 0 0-.01 M17 19a2 2 0 1 0 0-.01',
  ventas: 'M5 20V12 M12 20V5 M19 20v-9',
  tienda: 'M14 4h6v6 M20 4l-9 9 M18 14v5H5V6h5',
  salir: 'M15 4h4v16h-4 M10 8l-4 4 4 4 M6 12h10',
};

function Icono({ nombre }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" className="AdminIcono">
      <path d={ICONOS[nombre]} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Contenido del menú (se usa en la barra lateral y en el menú del celular)
function Navegacion({ pendientes, onNavegar, onCerrarSesion }) {
  const { pathname } = useLocation();

  return (
    <div className="AdminNavegacion">
      <Link to="/adminPanel" className="AdminMarca" onClick={onNavegar}>
        <img src={logo} alt="" width="36" height="36" />
        <span>Akash Store</span>
        <small>Panel</small>
      </Link>

      <nav className="AdminNav" aria-label="Secciones del panel">
        {SECCIONES.map((seccion) => (
          <div key={seccion.titulo} className="AdminNav__grupo">
            <p className="AdminNav__titulo">{seccion.titulo}</p>
            <ul>
              {seccion.enlaces.map((enlace) => {
                const activo = enlace.activoSi
                  ? enlace.activoSi(pathname)
                  : pathname === enlace.to || pathname.startsWith(`${enlace.to}/`);
                return (
                  <li key={enlace.to}>
                    <Link
                      to={enlace.to}
                      className={`AdminNav__enlace ${activo ? 'AdminNav__enlace--activo' : ''}`}
                      aria-current={activo ? 'page' : undefined}
                      onClick={onNavegar}
                    >
                      <Icono nombre={enlace.icono} />
                      <span>{enlace.texto}</span>
                      {enlace.conContador && pendientes > 0 && (
                        <span className="AdminNav__contador" aria-label={`${pendientes} pendientes`}>
                          {pendientes > 99 ? '99+' : pendientes}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="AdminNavegacion__pie">
        <a href="/" target="_blank" rel="noopener noreferrer" className="AdminNav__enlace">
          <Icono nombre="tienda" />
          <span>Ver la tienda</span>
        </a>
        <button type="button" className="AdminNav__enlace AdminNav__salir" onClick={onCerrarSesion}>
          <Icono nombre="salir" />
          <span>Cerrar sesión</span>
        </button>
      </div>
    </div>
  );
}

function AdminLayout({ children }) {
  const navigate = useNavigate();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [pendientes, setPendientes] = useState(0);
  const menuRef = useRef(null);

  // Contador de pedidos pendientes en «Pedidos». Si falla, simplemente no se muestra.
  useEffect(() => {
    let vigente = true;
    contarPedidosPendientes()
      .then((total) => {
        if (vigente) setPendientes(total);
      })
      .catch(() => {});
    return () => {
      vigente = false;
    };
  }, []);

  // Menú del celular: <dialog> nativo (foco atrapado, Esc y fondo oscuro, como el carrito)
  useEffect(() => {
    const dialogo = menuRef.current;
    if (!dialogo) return;
    if (menuAbierto && !dialogo.open) dialogo.showModal();
    if (!menuAbierto && dialogo.open) dialogo.close();
  }, [menuAbierto]);

  function cerrarSesion() {
    logout();
    navigate('/admin', { replace: true });
  }

  const cerrarMenu = () => setMenuAbierto(false);

  return (
    <div className="AdminPage">
      <aside className="AdminLateral">
        <Navegacion pendientes={pendientes} onCerrarSesion={cerrarSesion} />
      </aside>

      <div className="AdminContenido">
        {/* Solo en celular y tablet */}
        <header className="AdminBarra">
          <button
            type="button"
            className="AdminBarra__menu"
            onClick={() => setMenuAbierto(true)}
            aria-haspopup="dialog"
            aria-expanded={menuAbierto}
            aria-label={pendientes > 0 ? `Abrir menú, ${pendientes} pedidos pendientes` : 'Abrir menú'}
          >
            <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            {pendientes > 0 && <span className="AdminBarra__punto" aria-hidden="true" />}
          </button>
          <Link to="/adminPanel" className="AdminMarca">
            <img src={logo} alt="" width="32" height="32" />
            <span>Akash Store</span>
            <small>Panel</small>
          </Link>
        </header>

        <main className="AdminMain">{children}</main>
      </div>

      <dialog
        ref={menuRef}
        className="AdminMenu"
        aria-label="Menú del panel"
        onClose={cerrarMenu}
        onClick={(evento) => evento.target === evento.currentTarget && cerrarMenu()}
      >
        {menuAbierto && (
          <>
            <button type="button" className="AdminMenu__cerrar" onClick={cerrarMenu} aria-label="Cerrar menú">
              <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
            <Navegacion pendientes={pendientes} onNavegar={cerrarMenu} onCerrarSesion={cerrarSesion} />
          </>
        )}
      </dialog>
    </div>
  );
}

export default AdminLayout;
