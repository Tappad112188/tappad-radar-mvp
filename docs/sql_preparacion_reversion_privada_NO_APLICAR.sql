-- PREPARACION PARA REVISION. NO EJECUTAR EN SUPABASE PRODUCTIVO SIN APROBACION.
-- Requisitos verificados en consulta de solo lectura 2026-11-18:
-- pagos_tappad_estado_check no admite 'contracargo'; RLS habilitado en
-- pagos, suscripciones, acceso y activaciones.
-- Este script NO habilita LOGIN, NO instala jobs ni toca credenciales.
BEGIN;
DO $preflight$
DECLARE definicion text;
BEGIN
  SELECT pg_get_constraintdef(oid) INTO definicion
    FROM pg_constraint
   WHERE conrelid='public.pagos_tappad'::regclass
     AND conname='pagos_tappad_estado_check';
  IF definicion IS NULL
     OR definicion NOT LIKE '%reembolsado%'
     OR definicion NOT LIKE '%cancelado%'
     OR definicion LIKE '%contracargo%' THEN
    RAISE EXCEPTION 'Esquema de estados distinto al auditado; revisar manualmente';
  END IF;
END
$preflight$;
ALTER TABLE public.pagos_tappad DROP CONSTRAINT pagos_tappad_estado_check;
ALTER TABLE public.pagos_tappad ADD CONSTRAINT pagos_tappad_estado_check
  CHECK (estado IN ('pendiente','pagado','fallido','reembolsado','cancelado','contracargo'));

DO $roles$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='tappad_reversion_privada')
  THEN
    CREATE ROLE tappad_reversion_privada NOLOGIN NOINHERIT
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
END
$roles$;

-- El esquema y funcion de reversion deben existir antes de ejecutar.
ALTER TABLE tappad_internal.auditoria_estados_mercadopago ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON tappad_internal.auditoria_estados_mercadopago
  FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA tappad_internal TO tappad_reversion_privada;
GRANT SELECT ON public.suscripciones_tappad,public.pagos_tappad,
  public.acceso_comercial_tappad,public.activaciones_comerciales_tappad
  TO tappad_reversion_privada;
-- FOR UPDATE exige privilegio UPDATE en las filas bloqueadas.
GRANT UPDATE (estado) ON public.suscripciones_tappad TO tappad_reversion_privada;
GRANT UPDATE (estado) ON public.pagos_tappad TO tappad_reversion_privada;
GRANT UPDATE (estado,actualizado_en) ON public.acceso_comercial_tappad TO tappad_reversion_privada;
GRANT INSERT ON tappad_internal.auditoria_estados_mercadopago TO tappad_reversion_privada;
GRANT USAGE ON SEQUENCE tappad_internal.auditoria_estados_mercadopago_id_seq TO tappad_reversion_privada;
GRANT EXECUTE ON FUNCTION tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)
  TO tappad_reversion_privada;

CREATE POLICY tappad_reversion_lectura_sub ON public.suscripciones_tappad
  FOR SELECT TO tappad_reversion_privada USING (true);
CREATE POLICY tappad_reversion_bloqueo_sub ON public.suscripciones_tappad
  FOR UPDATE TO tappad_reversion_privada USING (true) WITH CHECK (true);
CREATE POLICY tappad_reversion_lectura_pago ON public.pagos_tappad
  FOR SELECT TO tappad_reversion_privada USING (true);
CREATE POLICY tappad_reversion_actualiza_pago ON public.pagos_tappad
  FOR UPDATE TO tappad_reversion_privada USING (true) WITH CHECK (true);
CREATE POLICY tappad_reversion_lectura_acceso ON public.acceso_comercial_tappad
  FOR SELECT TO tappad_reversion_privada USING (true);
CREATE POLICY tappad_reversion_actualiza_acceso ON public.acceso_comercial_tappad
  FOR UPDATE TO tappad_reversion_privada USING (true) WITH CHECK (true);
CREATE POLICY tappad_reversion_lectura_activaciones ON public.activaciones_comerciales_tappad
  FOR SELECT TO tappad_reversion_privada USING (true);
CREATE POLICY tappad_reversion_auditoria ON tappad_internal.auditoria_estados_mercadopago
  FOR INSERT TO tappad_reversion_privada WITH CHECK (true);
COMMIT;

-- NO conectar este rol a un login sin validar aislamiento de credenciales,
-- accesibilidad de tablas, RLS, search_path, funciones y acceso por API.
-- Las politicas USING(true) solo son aceptables si el rol privado permanece
-- estrictamente aislado, sin LOGIN, sin herencia desde roles publicos.
