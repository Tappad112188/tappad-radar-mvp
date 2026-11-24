-- Aplicada y verificada en Supabase el 24/11/2026.
BEGIN;
ALTER TABLE public.mercadopago_intentos_contratacion_tappad
 DROP CONSTRAINT mercadopago_intentos_contratacion_tappad_entorno_check,
 ADD CONSTRAINT mercadopago_intentos_contratacion_tappad_entorno_check CHECK (entorno IN ('prueba','produccion'));
COMMIT;
