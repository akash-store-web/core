-- =====================================================================================
-- ⚠️  EJECUTAR EN SUPABASE ANTES DEL MERGE del backend de intenciones (AKASH-168 y AKASH-180).
--     Si el backend se despliega sin estas tablas, producción responde 500 (pasó con HU033/HU034).
--
-- Akash Store · Sprint 3 · Intenciones por piedra (HU005, HU008 · AKASH-179)
-- Propuesto y ejecutado por: Diego (PO / BD), en el SQL Editor de Supabase
--
-- Cambios (aditivos e idempotentes; se puede volver a ejecutar sin efecto):
--   1. intencion: lista de 13 intenciones confirmada por la propietaria el 09/11/2026 (AKASH-178).
--   2. variante_intencion: intenciones de cada piedra. Va por VARIANTE y no por producto, porque las
--      piedras son variantes (la Pulsera de cuarzo tiene 12 piedras, cada una con sus intenciones).
--      Reglas de HU008: sin repetir (PK), máximo 5 por variante (trigger).
--   3. Carga inicial: 36 filas (piedra → intención), aplicadas a TODAS las variantes con ese nombre.
--   4. intencion.activa: la tabla intencion ya existía sin esa columna (el CREATE TABLE IF NOT EXISTS no la
--      agregó). ALTER aditivo ejecutado y verificado el 12/11/2026 (13 de 13 activas). HU005 E5.
--
-- Es transaccional: si algo falla, no queda nada a medias. No borra ni modifica datos existentes.
-- =====================================================================================
BEGIN;

-- ---------- 1. intencion ----------
CREATE TABLE IF NOT EXISTS public.intencion (
    id     SMALLSERIAL PRIMARY KEY,
    nombre VARCHAR(60) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT uq_intencion_nombre UNIQUE (nombre)
);

INSERT INTO public.intencion (nombre) VALUES
    ('Protección'),
    ('Abundancia y prosperidad'),
    ('Amor propio y sanación'),
    ('Calma y paz interior'),
    ('Claridad mental'),
    ('Comunicación'),
    ('Creatividad y motivación'),
    ('Energía y vitalidad'),
    ('Equilibrio emocional'),
    ('Intuición y conexión espiritual'),
    ('Buena suerte'),
    ('Transformación personal'),
    ('Confianza y fuerza personal')
ON CONFLICT (nombre) DO NOTHING;

-- ---------- 2. variante_intencion ----------
CREATE TABLE IF NOT EXISTS public.variante_intencion (
    variante_id  INTEGER  NOT NULL,
    intencion_id SMALLINT NOT NULL,
    CONSTRAINT pk_variante_intencion PRIMARY KEY (variante_id, intencion_id),   -- HU008 E5: sin repetir
    CONSTRAINT fk_vi_variante  FOREIGN KEY (variante_id)  REFERENCES public.variante(id) ON DELETE CASCADE,
    CONSTRAINT fk_vi_intencion FOREIGN KEY (intencion_id) REFERENCES public.intencion(id)
);
CREATE INDEX IF NOT EXISTS ix_vi_intencion ON public.variante_intencion (intencion_id);  -- filtro HU008

-- HU008 E6: máximo 5 intenciones por variante
CREATE OR REPLACE FUNCTION public.fn_max_5_intenciones() RETURNS trigger AS $$
BEGIN
    IF (SELECT count(*) FROM public.variante_intencion WHERE variante_id = NEW.variante_id) >= 5 THEN
        RAISE EXCEPTION 'Máximo 5 intenciones por variante (variante %)', NEW.variante_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tg_max_5_intenciones ON public.variante_intencion;
CREATE TRIGGER tg_max_5_intenciones BEFORE INSERT ON public.variante_intencion
    FOR EACH ROW EXECUTE FUNCTION public.fn_max_5_intenciones();

-- ---------- 3. Carga inicial (confirmada por la propietaria, AKASH-178) ----------
INSERT INTO public.variante_intencion (variante_id, intencion_id)
SELECT v.id, i.id
FROM (VALUES
    ('Amatista', 'Transformación personal'),
    ('Amatista', 'Protección'),
    ('Amatista', 'Equilibrio emocional'),
    ('Citrino', 'Abundancia y prosperidad'),
    ('Citrino', 'Energía y vitalidad'),
    ('Citrino', 'Creatividad y motivación'),
    ('Cuarzo ahumado', 'Protección'),
    ('Cuarzo ahumado', 'Transformación personal'),
    ('Cuarzo ahumado', 'Claridad mental'),
    ('Cuarzo rosa', 'Amor propio y sanación'),
    ('Cuarzo rosa', 'Calma y paz interior'),
    ('Howlita', 'Calma y paz interior'),
    ('Howlita', 'Comunicación'),
    ('Howlita', 'Intuición y conexión espiritual'),
    ('Jade', 'Protección'),
    ('Jade', 'Abundancia y prosperidad'),
    ('Jade', 'Buena suerte'),
    ('Labradorita', 'Intuición y conexión espiritual'),
    ('Labradorita', 'Creatividad y motivación'),
    ('Labradorita', 'Transformación personal'),
    ('Lapislázuli', 'Comunicación'),
    ('Lapislázuli', 'Protección'),
    ('Lapislázuli', 'Claridad mental'),
    ('Ojo de tigre', 'Protección'),
    ('Ojo de tigre', 'Confianza y fuerza personal'),
    ('Ojo de tigre', 'Claridad mental'),
    ('Ojo de tigre', 'Abundancia y prosperidad'),
    ('Piedra luna', 'Intuición y conexión espiritual'),
    ('Piedra luna', 'Equilibrio emocional'),
    ('Pirita', 'Abundancia y prosperidad'),
    ('Pirita', 'Confianza y fuerza personal'),
    ('Pirita', 'Energía y vitalidad'),
    ('Turmalina negra', 'Protección'),
    ('Obsidiana negra', 'Protección'),
    ('Obsidiana negra', 'Claridad mental'),
    ('Obsidiana negra', 'Equilibrio emocional')
) AS carga (piedra, intencion)
JOIN public.variante  v ON lower(v.nombre) = lower(carga.piedra)
JOIN public.intencion i ON i.nombre = carga.intencion
ON CONFLICT DO NOTHING;

-- ---------- Seguridad: igual que el resto de tablas (acceso solo vía FastAPI) ----------
ALTER TABLE public.intencion          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.variante_intencion ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON public.intencion, public.variante_intencion FROM anon, authenticated;

-- ---------- 4. intencion.activa (HU005 E5) ----------
-- La tabla intencion ya existía sin esta columna, así que el CREATE TABLE IF NOT EXISTS no la agregó.
-- Ejecutado y verificado el 12/11/2026 (13 de 13 activas).
ALTER TABLE public.intencion ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT true;

COMMIT;

-- ---------- Verificación (ejecutar después) ----------
-- 1) Deben salir 13 intenciones:
-- SELECT count(*) FROM public.intencion;
--
-- 2) Piedras con intenciones y cuántas variantes recibió cada una:
-- SELECT v.nombre AS piedra, count(DISTINCT v.id) AS variantes, string_agg(DISTINCT i.nombre, '; ') AS intenciones
--   FROM public.variante_intencion vi
--   JOIN public.variante v  ON v.id = vi.variante_id
--   JOIN public.intencion i ON i.id = vi.intencion_id
--  GROUP BY v.nombre ORDER BY v.nombre;
--
-- 3) Piedras de la carga que NO encontraron variante (revisar si el nombre difiere en la base):
-- SELECT p FROM unnest(ARRAY['Amatista', 'Citrino', 'Cuarzo ahumado', 'Cuarzo rosa', 'Howlita', 'Jade', 'Labradorita', 'Lapislázuli', 'Ojo de tigre', 'Piedra luna', 'Pirita', 'Turmalina negra', 'Obsidiana negra']) AS p
--  WHERE NOT EXISTS (SELECT 1 FROM public.variante v WHERE lower(v.nombre) = lower(p));
