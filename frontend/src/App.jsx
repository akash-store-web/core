import { Routes, Route } from 'react-router-dom';
import Login from './pages/admin/Login/Login.jsx';
import RecuperarContrasena from "./pages/admin/RecuperarContrasena/RecuperarContrasena.jsx";
import RestablecerContrasena from "./pages/admin/RestablecerContrasena/RestablecerContrasena.jsx";
import PanelAdmin from './pages/admin/PanelAdmin/PanelAdmin.jsx';
import ProductoForm from './pages/admin/ProductoForm/ProductoForm.jsx';
import EnviosAdmin from './pages/admin/Envios/EnviosAdmin.jsx';
import ComprasAdmin from './pages/admin/Compras/ComprasAdmin.jsx';
import CompraForm from './pages/admin/Compras/CompraForm.jsx';
import HomePage from './pages/Home/HomePage.jsx';
import CatalogoPage from './pages/Catalogo/CatalogoPage.jsx';
import FichaProductoPage from './pages/Catalogo/FichaProductoPage.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import PublicLayout from './components/PublicLayout.jsx';
import './App.css';

function App() {
  return (
    <Routes>
      {/* Páginas públicas: comparten cabecera y pie (PublicLayout + <Outlet />) */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/catalogo" element={<CatalogoPage />} />
        <Route path="/catalogo/:id" element={<FichaProductoPage />} />
      </Route>

      <Route path="/admin" element={<Login />} />
      <Route path="/recuperar" element={<RecuperarContrasena />} />
      <Route path="/restablecer" element={<RestablecerContrasena />} />
      <Route
        path="/adminPanel"
        element={
          <ProtectedRoute>
            <PanelAdmin />
          </ProtectedRoute>
        }
      />
      <Route
        path="/adminPanel/productos/nuevo"
        element={
          <ProtectedRoute>
            <ProductoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/adminPanel/productos/:id/editar"
        element={
          <ProtectedRoute>
            <ProductoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/adminPanel/compras"
        element={
          <ProtectedRoute>
            <ComprasAdmin />
          </ProtectedRoute>
        }
      />
      <Route
        path="/adminPanel/compras/nueva"
        element={
          <ProtectedRoute>
            <CompraForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/adminPanel/envios"
        element={
          <ProtectedRoute>
            <EnviosAdmin />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;