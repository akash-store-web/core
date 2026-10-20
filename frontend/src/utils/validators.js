export function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/*
  RUC peruano (11 dígitos). Valida el formato y el dígito verificador con el algoritmo módulo 11
  de SUNAT: un RUC inventado al azar casi nunca pasa. OJO: esto NO prueba que el RUC exista,
  solo que está bien formado.
*/
export function esRucValido(ruc) {
  if (!/^\d{11}$/.test(ruc)) return false;
  if (!['10', '15', '16', '17', '20'].includes(ruc.slice(0, 2))) return false;

  const pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const suma = pesos.reduce((acc, peso, i) => acc + peso * Number(ruc[i]), 0);
  const digito = (11 - (suma % 11)) % 10;
  return digito === Number(ruc[10]);
}

/*
  Lee los primeros bytes del archivo para saber qué es REALMENTE (no basta el nombre ni el
  tipo que declara el navegador: se pueden falsear con solo renombrar el archivo).
  Devuelve 'image/jpeg' | 'image/png' | 'image/webp' | 'application/pdf' | null.
*/
export async function tipoRealDeArchivo(archivo) {
  const bytes = new Uint8Array(await archivo.slice(0, 12).arrayBuffer());
  const texto = (desde, hasta) => String.fromCharCode(...bytes.slice(desde, hasta));

  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg';
  if (bytes[0] === 0x89 && texto(1, 4) === 'PNG') return 'image/png';
  if (texto(0, 4) === 'RIFF' && texto(8, 12) === 'WEBP') return 'image/webp';
  if (texto(0, 5) === '%PDF-') return 'application/pdf';
  return null;
}