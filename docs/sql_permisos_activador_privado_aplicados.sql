-- Applied 2026-11-14 to Supabase project rgzjrziulhobgjfhwvfw.
-- This role is NOLOGIN. Never expose a password, role membership or connection
-- string to browser or unprotected GitHub variables.
BEGIN;
GRANT SELECT ON TABLE public.suscripciones_tappad,public.pagos_tappad,public.planes_tappad,public.acceso_comercial_tappad,public.activaciones_comerciales_tappad TO tappad_activador_privado;
GRANT INSERT (cliente_id,suscripcion_id,pago_id,periodo_inicio,periodo_fin,estado,evidencia_proveedor) ON public.activaciones_comerciales_tappad TO tappad_activador_privado;
GRANT UPDATE (estado,fin_periodo,actualizado_en) ON public.suscripciones_tappad TO tappad_activador_privado;
GRANT INSERT (cliente_id,suscripcion_id,estado,origen,habilitado_desde,vigente_hasta,ultima_verificacion,actualizado_en) ON public.acceso_comercial_tappad TO tappad_activador_privado;
GRANT UPDATE (suscripcion_id,estado,origen,habilitado_desde,vigente_hasta,ultima_verificacion,actualizado_en) ON public.acceso_comercial_tappad TO tappad_activador_privado;
CREATE POLICY tappad_activador_select_pagos ON public.pagos_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_select_planes ON public.planes_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_select_suscripciones ON public.suscripciones_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_update_suscripciones ON public.suscripciones_tappad FOR UPDATE TO tappad_activador_privado USING (true) WITH CHECK (true);
CREATE POLICY tappad_activador_select_acceso ON public.acceso_comercial_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_insert_acceso ON public.acceso_comercial_tappad FOR INSERT TO tappad_activador_privado WITH CHECK (true);
CREATE POLICY tappad_activador_update_acceso ON public.acceso_comercial_tappad FOR UPDATE TO tappad_activador_privado USING (true) WITH CHECK (true);
CREATE POLICY tappad_activador_select_activaciones ON public.activaciones_comerciales_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_insert_activaciones ON public.activaciones_comerciales_tappad FOR INSERT TO tappad_activador_privado WITH CHECK (true);
COMMIT;
-- Caveat: the role has table DML privileges; its login credential must be
-- isolated. Consider narrowing DML through an audited SECURITY DEFINER
-- function before allowing production payments. Do not deploy a login yet.
