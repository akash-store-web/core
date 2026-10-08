import { API_URL, USE_MOCK } from './config.js';

const MENSAJE_GENERICO =
  'Si el correo está registrado, te enviaremos un enlace para restablecer tu contraseña';
const MENSAJE_ENLACE_INVALIDO = 'El enlace no es válido o ya venció; solicita uno nuevo';

// Pide el enlace de recuperación (HU024, escenarios 1 y 2).
// El backend responde SIEMPRE lo mismo, exista o no el correo.
export async function solicitarRecuperacion(email) {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return MENSAJE_GENERICO;
  }

  let response;
  try {
    response = await fetch(`${API_URL}/auth/recuperar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor. Intenta de nuevo.');
  }

  if (response.status === 422) {
    throw new Error('Ingresa un correo válido.');
  }
  if (!response.ok) {
    throw new Error('Ocurrió un error en el servidor. Intenta de nuevo.');
  }

  const data = await response.json();
  return data.detail ?? MENSAJE_GENERICO;
}

// Guarda la nueva contraseña con el token del enlace (HU024, escenario 3).
// Si el enlace venció, ya se usó o no es válido, el error trae enlaceInvalido = true.
export async function restablecerContrasena(token, nuevaContrasena) {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    if (token === 'vencido') {
      const error = new Error(MENSAJE_ENLACE_INVALIDO);
      error.enlaceInvalido = true;
      throw error;
    }
    return 'Contraseña actualizada; ya puedes iniciar sesión';
  }

  let response;
  try {
    response = await fetch(`${API_URL}/auth/restablecer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, nueva_contrasena: nuevaContrasena }),
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor. Intenta de nuevo.');
  }

  if (response.status === 400) {
    const error = new Error(MENSAJE_ENLACE_INVALIDO);
    error.enlaceInvalido = true;
    throw error;
  }
  if (response.status === 422) {
    throw new Error('La contraseña debe tener entre 8 y 72 caracteres.');
  }
  if (!response.ok) {
    throw new Error('Ocurrió un error en el servidor. Intenta de nuevo.');
  }

  const data = await response.json();
  return data.detail ?? 'Contraseña actualizada; ya puedes iniciar sesión';
}