-- =====================================================================================
-- ⚠️  EJECUTAR EN SUPABASE ANTES DEL MERGE de la rama feature/HU010-pedido-whatsapp-AKASH-correa.
--     Sin este cambio, POST /pedidos responde 500 en producción (pasó con HU033/HU034).
--
-- Akash Store · Sprint 3 · HU010 Enviar mi pedido por WhatsApp (AKASH-83)
-- Propuesto por: Raúl (backend) · Revisa y ejecuta: Diego (PO / BD), en el SQL Editor de Supabase
--
-- Por qué: con la venta por WhatsApp (decisión del PO del 10/11/2026) la clienta solo deja nombre,
-- celular, distrito y modalidad de entrega. Hoy cliente.correo y cliente.direccion son NOT NULL,
-- así que el pedido no se podría guardar sin inventar datos.
--
-- Cambios (idempotentes; se puede volver a ejecutar sin efecto):
--   1. cliente.correo pasa a opcional.
--   2. cliente.direccion pasa a opcional (para delivery se coordina por el chat si no la deja).
--
-- No borra ni modifica datos existentes (hoy la tabla cliente está vacía). Es transaccional.
-- Los estados nuevos del pedido (pendiente, confirmado, cancelado, enviado, entregado) NO requieren
-- cambio: pedido.estado es VARCHAR(20) sin restricción.
-- =====================================================================================
BEGIN;

ALTER TABLE public.cliente ALTER COLUMN correo DROP NOT NULL;
ALTER TABLE public.cliente ALTER COLUMN direccion DROP NOT NULL;

COMMIT;

-- ---------- Verificación (debe decir YES en las dos filas) ----------
SELECT column_name, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'cliente' AND column_name IN ('correo', 'direccion');
