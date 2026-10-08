import { API_URL } from './config.js';
import { getToken, logout } from './authService.js';

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// Convierte el "detail" de FastAPI en un texto legible (puede ser texto o lista).
export function mensajeDeError(detail) {
  if (Array.isArray(detail)) {
    return detail.map((e) => `${e.loc?.at(-1)}: ${e.msg}`).join('\n');
  }
  return typeof detail === 'string' ? detail : 'Ocurrió un error inesperado.';
}

// Petición al backend con el token de la sesión.
// Si responde 401, cierra la sesión y manda al login (HU023).
export async function apiFetch(path, { method = 'GET', body, formData } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (formData) {
    payload = formData; // sin Content-Type: lo pone el navegador
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError('No se pudo conectar con el servidor.', 0);
  }

  if (response.status === 401) {
    logout();
    window.location.assign('/admin');
    throw new ApiError('Tu sesión expiró. Inicia sesión de nuevo.', 401);
  }
  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(mensajeDeError(data?.detail), response.status, data?.detail);
  }
  return data;
}