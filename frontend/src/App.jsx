import { Routes, Route } from 'react-router-dom';
import Login from './pages/admin/Login/Login.jsx';
import RecuperarContrasena from './pages/admin/RecuperarContrasena/RecuperarContrasena.jsx';
import RestablecerContrasena from './pages/admin/RestablecerContrasena/RestablecerContrasena.jsx';
import PanelAdmin from './pages/admin/PanelAdmin/PanelAdmin.jsx';
import HomePage from './pages/Home/HomePage.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import './App.css';

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
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
    </Routes>
  );
}

export default App;
