// Los montos llegan del backend como texto con 2 decimales ("25.00").
export const soles = (monto) => `S/ ${Number(monto).toFixed(2)}`;

// Las fechas llegan como "2026-10-14"; se muestran como "14/10/2026".
export const fechaCorta = (iso) => {
  const [anio, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${anio}`;
};

// Primer día del mes actual (AAAA-MM-DD): límite inferior de la fecha de una compra.
export const primerDiaMesISO = () => {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-01`;
};

// Fecha de hoy en la hora del navegador, con formato AAAA-MM-DD (toISOString usaría UTC y puede adelantar el día).
export const hoyISO = () => {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, '0');
  const dia = String(ahora.getDate()).padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-${dia}`;
};