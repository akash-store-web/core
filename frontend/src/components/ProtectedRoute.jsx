import { Navigate } from 'react-router-dom';
import { isAuthenticated } from '../services/authService.js';

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/admin" replace />;
  }
  return children;
}

export default ProtectedRoute;