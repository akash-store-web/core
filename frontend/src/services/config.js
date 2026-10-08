export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// true = el frontend funciona con datos simulados, sin backend.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';