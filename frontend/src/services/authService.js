import { API_URL, USE_MOCK } from './config.js';

const TOKEN_KEY = 'akash_token';

export async function login(email, password) {
  // Modo simulado: solo para desarrollar mientras el backend no esté encendido.
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    if (email === 'admin@akash.com' && password === '123456') {
      localStorage.setItem(TOKEN_KEY, 'mock-token');
      return { access_token: 'mock-token' };
    }
    throw new Error('Correo o contraseña incorrectos.');
  }

  let response;
  try {
    response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor.');
  }

  if (response.status === 401) {
    throw new Error('Correo o contraseña incorrectos.');
  }
  if (response.status === 422) {
    throw new Error('Revisa el formato de tu correo y contraseña.');
  }
  if (!response.ok) {
    throw new Error('Ocurrió un error en el servidor. Intenta de nuevo.');
  }

  const data = await response.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  return data;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
}

// Lee la fecha de expiración (campo "exp") del JWT, en milisegundos.
// Solo mejora la experiencia: la validación real la hace el backend.
function getTokenExpiry(token) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const { exp } = JSON.parse(atob(payload));
    return typeof exp === 'number' ? exp * 1000 : null;
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  const token = getToken();
  if (!token) return false;

  // El token simulado no es un JWT real.
  if (USE_MOCK && token === 'mock-token') return true;

  const expiry = getTokenExpiry(token);
  if (expiry === null || Date.now() >= expiry) {
    logout();
    return false;
  }
  return true;
}