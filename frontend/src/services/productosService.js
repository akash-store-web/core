import { USE_MOCK } from './config.js';
import { apiFetch } from './http.js';

const PLACEHOLDER = '/placeholder-producto.webp';
const esperar = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

/* ------------------------------------------------------------------ */
/*  DATOS SIMULADOS (solo se usan con VITE_USE_MOCK=true)              */
/*  Viven en memoria: al recargar la página vuelven al estado inicial. */
/* ------------------------------------------------------------------ */

let siguienteProductoId = 4;
let siguienteVarianteId = 6;

const categoriasMock = [
  { id: 1, nombre: 'Boxes y kits', orden: 1 },
  { id: 2, nombre: 'Pulseras', orden: 2 },
  { id: 3, nombre: 'Collares', orden: 3 },
  { id: 4, nombre: 'Anillos', orden: 4 },
  { id: 5, nombre: 'Cuarzos en bruto', orden: 5 },
  { id: 6, nombre: 'Roll on', orden: 6 },
  { id: 7, nombre: 'Inciensos', orden: 7 },
];

const productosMock = [
  {
    id: 1,
    categoria_id: 4,
    nombre: 'Anillo de plata 925 con piedra',
    precio_base: '40.00',
    publicado: true,
    fotos: [],
    variantes: [
      { id: 1, nombre: 'Amatista', precio: '45.00', existencias: 3, propiedades: 'Se le atribuye calma.' },
      { id: 2, nombre: 'Turmalina negra', precio: null, existencias: 0, propiedades: null },
    ],
  },
  {
    id: 2,
    categoria_id: 2,
    nombre: 'Pulsera de cuarzo',
    precio_base: '45.00',
    publicado: false,
    fotos: [],
    variantes: [
      { id: 3, nombre: 'Cuarzo rosa', precio: null, existencias: 5, propiedades: 'Amor propio y armonía.' },
      { id: 4, nombre: 'Pirita', precio: null, existencias: 2, propiedades: null },
    ],
  },
  {
    id: 3,
    categoria_id: 1,
    nombre: 'Spray áurico',
    precio_base: '25.00',
    publicado: true,
    fotos: [],
    variantes: [{ id: 5, nombre: 'Única', precio: null, existencias: 8, propiedades: null }],
  },
];

function aItemLista(p) {
  const existenciasTotal = p.variantes.reduce((suma, v) => suma + v.existencias, 0);
  const foto = p.fotos[0];
  return {
    id: p.id,
    nombre: p.nombre,
    categoria_id: p.categoria_id,
    categoria: categoriasMock.find((c) => c.id === p.categoria_id)?.nombre ?? '',
    precio_base: p.precio_base,
    publicado: p.publicado,
    num_variantes: p.variantes.length,
    existencias_total: existenciasTotal,
    agotado: existenciasTotal <= 0,
    foto_principal: foto ? foto.url : PLACEHOLDER,
    foto_generica: !foto,
  };
}

function aVarianteOut(p, v) {
  return {
    id: v.id,
    producto_id: p.id,
    nombre: v.nombre,
    precio: v.precio,
    precio_efectivo: v.precio ?? p.precio_base,
    existencias: v.existencias,
    agotado: v.existencias <= 0,
    propiedades: v.propiedades,
  };
}

/* ------------------------------------------------------------------ */
/*  FUNCIONES QUE USA LA INTERFAZ                                      */
/* ------------------------------------------------------------------ */

export async function listarCategorias() {
  if (USE_MOCK) {
    await esperar(200);
    return categoriasMock;
  }
  return apiFetch('/admin/categorias');
}

export async function listarProductos({ q = '', categoriaId = '' } = {}) {
  if (USE_MOCK) {
    await esperar();
    const texto = q.trim().toLowerCase();
    return productosMock
      .filter((p) => !texto || p.nombre.toLowerCase().includes(texto))
      .filter((p) => !categoriaId || p.categoria_id === Number(categoriaId))
      .map(aItemLista);
  }
  const params = new URLSearchParams();
  if (q.trim()) params.set('q', q.trim());
  if (categoriaId) params.set('categoria_id', categoriaId);
  const query = params.toString();
  return apiFetch(`/admin/productos${query ? `?${query}` : ''}`);
}

export async function listarVariantes(productoId) {
  if (USE_MOCK) {
    await esperar(250);
    const producto = productosMock.find((p) => p.id === productoId);
    return producto ? producto.variantes.map((v) => aVarianteOut(producto, v)) : [];
  }
  return apiFetch(`/admin/productos/${productoId}/variantes`);
}

// HU016: interruptor Activo / Inactivo. Despublicar no borra nada.
export async function cambiarPublicado(productoId, publicado) {
  if (USE_MOCK) {
    await esperar(300);
    const producto = productosMock.find((p) => p.id === productoId);
    if (!producto) throw new Error('El producto no existe.');
    producto.publicado = publicado;
    return { id: producto.id, publicado };
  }
  return apiFetch(`/admin/productos/${productoId}/publicado`, {
    method: 'PATCH',
    body: { publicado },
  });
}

/*
  HU014 + HU027: registra el producto completo.
  `datos` = { categoria_id, nombre, descripcion, precio_base, material, medidas,
              peso_g, es_pieza_natural, existencias, propiedades,
              variantes: [{ nombre, precio, existencias, propiedades }] }
  `fotos` = lista de File (la primera queda como principal).
*/
export async function crearProducto(datos, fotos) {
  if (USE_MOCK) return crearProductoMock(datos, fotos);
  return crearProductoReal(datos, fotos);
}

async function crearProductoMock(datos, fotos) {
  await esperar(700);
  const variantes = datos.variantes.length
    ? datos.variantes.map((v) => ({
        id: siguienteVarianteId++,
        nombre: v.nombre,
        precio: v.precio,
        existencias: v.existencias,
        propiedades: v.propiedades,
      }))
    : [
        {
          id: siguienteVarianteId++,
          nombre: 'Única',
          precio: null,
          existencias: datos.existencias,
          propiedades: datos.propiedades,
        },
      ];

  const producto = {
    id: siguienteProductoId++,
    categoria_id: datos.categoria_id,
    nombre: datos.nombre,
    precio_base: datos.precio_base,
    publicado: false, // HU016 escenario 3: todo producto nuevo nace sin publicar
    fotos: fotos.map((archivo) => ({ url: URL.createObjectURL(archivo) })),
    variantes,
  };
  productosMock.unshift(producto);
  return { id: producto.id, nombre: producto.nombre, publicado: false };
}

async function crearProductoReal(datos, fotos) {
  const tieneVariantes = datos.variantes.length > 0;

  // 1. El producto nace con una variante "Única" que guarda sus existencias.
  const producto = await apiFetch('/admin/productos', {
    method: 'POST',
    body: {
      categoria_id: datos.categoria_id,
      nombre: datos.nombre,
      descripcion: datos.descripcion,
      precio_base: datos.precio_base,
      material: datos.material,
      medidas: datos.medidas,
      peso_g: datos.peso_g,
      es_pieza_natural: datos.es_pieza_natural,
      existencias: tieneVariantes ? datos.variantes[0].existencias : datos.existencias,
    },
  });

  try {
    // 2. Variantes: la primera se registra renombrando la "Única"; las demás se agregan.
    if (tieneVariantes || datos.propiedades) {
      const [unica] = await apiFetch(`/admin/productos/${producto.id}/variantes`);

      if (tieneVariantes) {
        const [primera, ...otras] = datos.variantes;
        await apiFetch(`/admin/productos/${producto.id}/variantes/${unica.id}`, {
          method: 'PUT',
          body: primera,
        });
        for (const variante of otras) {
          await apiFetch(`/admin/productos/${producto.id}/variantes`, {
            method: 'POST',
            body: variante,
          });
        }
      } else {
        await apiFetch(`/admin/productos/${producto.id}/variantes/${unica.id}`, {
          method: 'PUT',
          body: {
            nombre: unica.nombre,
            precio: null,
            existencias: datos.existencias,
            propiedades: datos.propiedades,
          },
        });
      }
    }

    // 3. Fotos: una por petición y en orden; la primera queda como principal.
    for (const archivo of fotos) {
      const formData = new FormData();
      formData.append('foto', archivo);
      await apiFetch(`/admin/productos/${producto.id}/imagenes`, {
        method: 'POST',
        formData,
      });
    }
  } catch (err) {
    const parcial = new Error(
      `El producto se guardó (sin publicar), pero no se pudo completar: ${err.message}`,
    );
    parcial.productoId = producto.id;
    throw parcial;
  }

  return producto;
}

/*
  HU015: ajusta las existencias de UNA variante desde el listado.
  `cambio` = { cambio: -1 } (botones − / +)  o  { existencias: 12 } (cantidad exacta).
  Responde { id, producto_id, existencias, agotado }.
*/
export async function ajustarStock(varianteId, cambio) {
  if (USE_MOCK) {
    await esperar(250);
    for (const producto of productosMock) {
      const variante = producto.variantes.find((v) => v.id === varianteId);
      if (!variante) continue;

      const nuevas = cambio.existencias ?? variante.existencias + cambio.cambio;
      if (nuevas < 0) throw new Error('Las existencias no pueden quedar en negativo');

      variante.existencias = nuevas;
      return {
        id: variante.id,
        producto_id: producto.id,
        existencias: nuevas,
        agotado: nuevas <= 0,
      };
    }
    throw new Error('Variante no encontrada');
  }
  return apiFetch(`/admin/variantes/${varianteId}/stock`, {
    method: 'PATCH',
    body: cambio,
  });
}