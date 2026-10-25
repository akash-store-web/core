import { useEffect } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import logo from '../assets/logo.png';
import './PublicLayout.css';

// Enlaces del menú público. Agregar aquí las secciones nuevas (Ofertas, Contacto…)
// para que aparezcan a la vez en la cabecera y en el pie.
const ENLACES = [
  { to: '/', texto: 'Inicio', end: true },
  { to: '/catalogo', texto: 'Catálogo' },
];

function PublicLayout() {
  const { pathname } = useLocation();

  // Al cambiar de página, volver arriba (el navegador no lo hace solo en una SPA).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="PublicPage">
      <a href="#contenido" className="PublicSaltar">
        Saltar al contenido
      </a>

      <header className="PublicHeader">
        <div className="PublicHeader__inner">
          <Link to="/" className="PublicMarca" aria-label="Akash Store, ir al inicio">
            <img src={logo} alt="" width="40" height="40" />
            <span className="PublicMarca__nombre">Akash Store</span>
          </Link>

          <nav className="PublicNav" aria-label="Principal">
            {ENLACES.map((enlace) => (
              <NavLink key={enlace.to} to={enlace.to} end={enlace.end}>
                {enlace.texto}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main id="contenido" className="PublicMain" tabIndex={-1}>
        <Outlet />
      </main>

      <footer className="PublicFooter">
        <div className="PublicFooter__inner">
          <div className="PublicFooter__marca">
            <span className="PublicFooter__nombre">Akash Store Perú</span>
            <p>Cuarzos, joyería de plata e inciensos.</p>
          </div>

          <nav className="PublicFooter__nav" aria-label="Pie de página">
            {ENLACES.map((enlace) => (
              <Link key={enlace.to} to={enlace.to}>
                {enlace.texto}
              </Link>
            ))}
          </nav>

          <p className="PublicFooter__legal">
            © {new Date().getFullYear()} Akash Store Perú
          </p>
        </div>
      </footer>
    </div>
  );
}

export default PublicLayout;
