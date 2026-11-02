-- =====================================================================================
-- ⚠️  EJECUTAR EN SUPABASE ANTES DEL MERGE de la rama feature/T07-validaciones-backend-AKASH-correa.
--     Si el backend se despliega sin estas columnas, producción responde 500 (pasó con HU033/HU034).
--
-- Akash Store · Sprint 2 · Validaciones y escenarios de error (T-07 / AKASH-148, HU032, HU033, HU034, AKASH-152)
-- Propuesto por: Raúl (backend) · Revisa y ejecuta: Diego (PO / BD), en el SQL Editor de Supabase
--
-- Cambios (todos aditivos e idempotentes; se puede volver a ejecutar sin efecto):
--   1. variante.activa: una variante con historial (movimientos, compras o pedidos) no se borra,
--      se desactiva (HU027 E9, HU032 E8, HU033 E16, HU028 E8). Las existentes quedan activas.
--   2. producto.actualizado_en: control de edición simultánea en el panel (HU032 E10).
--      Las filas existentes toman la fecha de creación.
--   3. compra.tipo_comprobante admite 'sin_comprobante' (HU033 escenario 6 / AKASH-152), con número
--      interno SC-0001, SC-0002… La columna pasa de VARCHAR(10) a VARCHAR(20) porque
--      'sin_comprobante' tiene 15 caracteres (ampliar un VARCHAR no reescribe la tabla).
--
-- Es transaccional: si algo falla, no queda nada a medias. No borra ni modifica datos existentes.
-- =====================================================================================
BEGIN;

-- ---------- 1. variante.activa ----------
ALTER TABLE public.variante
    ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT true;

-- ---------- 2. producto.actualizado_en ----------
-- Solo la primera vez: crea la columna y copia la fecha de creación en las filas existentes.
-- Al volver a ejecutar el script no se toca (no pisa fechas de ediciones posteriores).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'producto' AND column_name = 'actualizado_en') THEN
        ALTER TABLE public.producto ADD COLUMN actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now();
        UPDATE public.producto SET actualizado_en = creado_en;
    END IF;
END $$;

-- ---------- 3. compra.tipo_comprobante con 'sin_comprobante' ----------
ALTER TABLE public.compra ALTER COLUMN tipo_comprobante TYPE VARCHAR(20);
ALTER TABLE public.compra DROP CONSTRAINT IF EXISTS ck_compra_tipo;
ALTER TABLE public.compra
    ADD CONSTRAINT ck_compra_tipo CHECK (tipo_comprobante IN ('boleta', 'factura', 'sin_comprobante'));

-- ---------- Seguridad (sin cambios: las tablas ya tienen RLS; se reafirma por si acaso) ----------
ALTER TABLE public.variante ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.producto ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compra   ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON public.variante, public.producto, public.compra FROM anon, authenticated;

COMMIT;

-- ---------- Verificación (ejecutar después, solo lectura) ----------
-- SELECT table_name, column_name, data_type, is_nullable, column_default
--   FROM information_schema.columns
--  WHERE table_schema = 'public'
--    AND ((table_name = 'variante' AND column_name = 'activa')
--      OR (table_name = 'producto' AND column_name = 'actualizado_en')
--      OR (table_name = 'compra'   AND column_name = 'tipo_comprobante'));
-- SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_compra_tipo';
