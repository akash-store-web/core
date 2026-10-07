// Los montos llegan del backend como texto con 2 decimales ("25.00").
export const soles = (monto) => `S/ ${Number(monto).toFixed(2)}`;