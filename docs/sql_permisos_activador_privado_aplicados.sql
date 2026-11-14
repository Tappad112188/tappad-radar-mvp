-- Final hardening applied 2026-11-14.
-- Privileged function stays in unexposed tappad_internal schema with fixed
-- search_path. Owner postgres. Dedicated role remains NOLOGIN.
-- WARNING: function trusts caller-supplied JSON evidence; do not enable login
-- or production activation until cryptographic/provider verification is
-- enforced in the trusted worker and credential isolation is reviewed.
BEGIN;
ALTER FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb) SECURITY DEFINER;
REVOKE ALL PRIVILEGES ON TABLE public.suscripciones_tappad,public.pagos_tappad,public.planes_tappad,public.acceso_comercial_tappad,public.activaciones_comerciales_tappad FROM tappad_activador_privado;
DROP POLICY IF EXISTS tappad_activador_select_pagos ON public.pagos_tappad;
DROP POLICY IF EXISTS tappad_activador_select_planes ON public.planes_tappad;
DROP POLICY IF EXISTS tappad_activador_select_suscripciones ON public.suscripciones_tappad;
DROP POLICY IF EXISTS tappad_activador_update_suscripciones ON public.suscripciones_tappad;
DROP POLICY IF EXISTS tappad_activador_select_acceso ON public.acceso_comercial_tappad;
DROP POLICY IF EXISTS tappad_activador_insert_acceso ON public.acceso_comercial_tappad;
DROP POLICY IF EXISTS tappad_activador_update_acceso ON public.acceso_comercial_tappad;
DROP POLICY IF EXISTS tappad_activador_select_activaciones ON public.activaciones_comerciales_tappad;
DROP POLICY IF EXISTS tappad_activador_insert_activaciones ON public.activaciones_comerciales_tappad;
REVOKE ALL ON FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb) TO tappad_activador_privado;
COMMIT;

-- Read-only access for the trusted worker's cycle lookup (applied).
-- No direct INSERT/UPDATE/DELETE granted to this role.
BEGIN;
GRANT SELECT ON public.pagos_tappad,public.suscripciones_tappad,public.planes_tappad,public.acceso_comercial_tappad TO tappad_activador_privado;
CREATE POLICY tappad_activador_lectura_pagos ON public.pagos_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_lectura_suscripciones ON public.suscripciones_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_lectura_planes ON public.planes_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_lectura_acceso ON public.acceso_comercial_tappad FOR SELECT TO tappad_activador_privado USING (true);
COMMIT;
