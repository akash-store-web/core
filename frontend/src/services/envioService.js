import { USE_MOCK } from './config.js';
import { apiFetch } from './http.js';

const esperar = (ms = 350) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  DATOS SIMULADOS (solo con VITE_USE_MOCK=true; viven en memoria)    */
/* ------------------------------------------------------------------ */

let siguienteZonaId = 2;

const zonasMock = [{ id: 1, nombre: 'Lima — motorizado', costo: '10.00', activa: true }];

const distritosMock = [
  'Barranco', 'Breña', 'Callao', 'Chorrillos', 'Jesús María', 'La Molina', 'Lince',
  'Magdalena del Mar', 'Miraflores', 'Pueblo Libre', 'San Borja', 'San Isidro',
  'San Miguel', 'Santiago de Surco', 'Surquillo',
].map((nombre, i) => ({
  id: i + 1,
  nombre,
  zona_envio_id: ['Miraflores', 'San Isidro', 'Barranco'].includes(nombre) ? 1 : null,
}));

const zonaDe = (distrito) => zonasMock.find((z) => z.id === distrito.zona_envio_id);
const conCobertura = (distrito) => Boolean(zonaDe(distrito)?.activa);

const aZonaOut = (zona) => ({
  ...zona,
  num_distritos: distritosMock.filter((d) => d.zona_envio_id === zona.id).length,
});

/* ------------------------------------------------------------------ */
/*  PANEL (HU026 escenarios 1 y 4)                                     */
/* ------------------------------------------------------------------ */

export async function listarZonas() {
  if (USE_MOCK) {
    await esperar();
    return zonasMock.map(aZonaOut);
  }
  return apiFetch('/admin/zonas-envio');
}

// datos = { nombre, costo: "10.00", activa: true }
export async function crearZona(datos) {
  if (USE_MOCK) {
    await esperar();
    const zona = { id: siguienteZonaId++, ...datos };
    zonasMock.push(zona);
    return aZonaOut(zona);
  }
  return apiFetch('/admin/zonas-envio', { method: 'POST', body: datos });
}

export async function actualizarZona(zonaId, datos) {
  if (USE_MOCK) {
    await esperar(250);
    const zona = zonasMock.find((z) => z.id === zonaId);
    if (!zona) throw new Error('Zona de envío no encontrada');
    Object.assign(zona, datos);
    return aZonaOut(zona);
  }
  return apiFetch(`/admin/zonas-envio/${zonaId}`, { method: 'PUT', body: datos });
}

export async function listarDistritos() {
  if (USE_MOCK) {
    await esperar();
    return distritosMock.map((d) => ({ ...d, con_cobertura: conCobertura(d) }));
  }
  return apiFetch('/admin/distritos');
}

/*
  Deja la zona con exactamente los distritos elegidos.
  - agregarIds: distritos que pasan a esta zona (el backend los mueve si estaban en otra).
  - quitar: [{ id, nombre }] distritos que salen de la zona y quedan SIN cobertura.
*/
export async function guardarDistritosDeZona(zonaId, agregarIds, quitar) {
  if (USE_MOCK) {
    await esperar();
    distritosMock.forEach((d) => {
      if (agregarIds.includes(d.id)) d.zona_envio_id = zonaId;
      if (quitar.some((q) => q.id === d.id)) d.zona_envio_id = null;
    });
    return;
  }

  if (agregarIds.length > 0) {
    await apiFetch(`/admin/zonas-envio/${zonaId}/distritos`, {
      method: 'PUT',
      body: { distrito_ids: agregarIds },
    });
  }
  for (const distrito of quitar) {
    await apiFetch(`/admin/distritos/${distrito.id}`, {
      method: 'PUT',
      body: { nombre: distrito.nombre, zona_envio_id: null },
    });
  }
}

/* ------------------------------------------------------------------ */
/*  PÚBLICO, para el checkout (HU026 escenarios 2, 3 y 4). Sin login.  */
/* ------------------------------------------------------------------ */

// [{ id, nombre, con_cobertura, costo_envio: "10.00" | null }]
export async function listarDistritosPublicos() {
  if (USE_MOCK) {
    await esperar(200);
    return distritosMock.map((d) => ({
      id: d.id,
      nombre: d.nombre,
      con_cobertura: conCobertura(d),
      costo_envio: conCobertura(d) ? zonaDe(d).costo : null,
    }));
  }
  return apiFetch('/envio/distritos');
}

// { distrito_id, distrito, con_cobertura, costo_envio }
export async function consultarCostoEnvio(distritoId) {
  if (USE_MOCK) {
    await esperar(200);
    const distrito = distritosMock.find((d) => d.id === Number(distritoId));
    if (!distrito) throw new Error('Distrito no encontrado');
    return {
      distrito_id: distrito.id,
      distrito: distrito.nombre,
      con_cobertura: conCobertura(distrito),
      costo_envio: conCobertura(distrito) ? zonaDe(distrito).costo : null,
    };
  }
  return apiFetch(`/envio/costo?distrito_id=${distritoId}`);
}