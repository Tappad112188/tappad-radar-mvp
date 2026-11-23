-- FUNCION PRIVADA NO EXPUESTA; SIN GRANTS; NO AUTORIZAR DESDE API PUBLICA.\n-- Solo aplicar si el proceso servidor verifica la evidencia en Mercado Pago.\n-- BORRADOR NO APLICADO. Solo ejecutar tras validar proveedor en servidor.
-- Nunca aceptar evidencia JSON del navegador como verificacion de pago.
-- El llamador de confianza debe consultar API de Mercado Pago, verificar
-- identidad del vendedor, preapproval, payment, importe, moneda y periodo.
-- Este procedimiento aplica atomicamente una evidencia previamente validada.
CREATE OR REPLACE FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(
 p_cliente bigint, p_suscripcion bigint, p_pago bigint,
 p_inicio timestamptz, p_fin timestamptz, p_evidencia jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
DECLARE
 v_sub public.suscripciones_tappad%ROWTYPE;
 v_pago public.pagos_tappad%ROWTYPE;
 v_plan public.planes_tappad%ROWTYPE;
 v_activacion bigint;
 v_fin_anterior timestamptz;
 v_inicio_esperado timestamptz;
BEGIN
 IF p_cliente IS NULL OR p_suscripcion IS NULL OR p_pago IS NULL
    OR p_inicio IS NULL OR p_fin IS NULL OR p_evidencia IS NULL
    OR p_inicio > transaction_timestamp()
    OR p_fin <= transaction_timestamp() OR p_fin <= p_inicio
    OR p_evidencia->>'verificacion_remota' IS DISTINCT FROM 'confirmada'
    OR p_evidencia->>'entorno' IS DISTINCT FROM 'produccion'
    OR nullif(p_evidencia->>'seller_id','') IS NULL THEN
   RETURN false;
 END IF;
 SELECT * INTO v_sub FROM public.suscripciones_tappad
  WHERE id=p_suscripcion AND cliente_id=p_cliente
  FOR UPDATE;
 IF NOT FOUND OR v_sub.proveedor_cobro IS DISTINCT FROM 'mercadopago_produccion'
    OR v_sub.estado NOT IN ('pendiente','activa') OR
    nullif(btrim(v_sub.referencia_externa),'') IS NULL THEN RETURN false; END IF;
 SELECT * INTO v_plan FROM public.planes_tappad WHERE id=v_sub.plan_id;
 IF NOT FOUND OR NOT v_plan.activo OR v_plan.periodicidad NOT IN ('mensual','anual') THEN RETURN false; END IF;
 -- Una renovacion solo extiende el periodo previo; nunca lo acorta
 -- ni crea un hueco o solapamiento entre ciclos.
 SELECT vigente_hasta INTO v_fin_anterior
 FROM public.acceso_comercial_tappad
 WHERE cliente_id=p_cliente FOR UPDATE;
 IF v_fin_anterior IS NOT NULL THEN
   v_inicio_esperado := v_fin_anterior;
   IF p_inicio <> v_inicio_esperado OR p_fin <= v_fin_anterior THEN
     RETURN false;
   END IF;
 ELSE
   -- Primer ciclo: inicio no puede ser futuro ni arbitrariamente antiguo.
   IF p_inicio < transaction_timestamp() - interval '7 days' THEN
     RETURN false;
   END IF;
 END IF;
 -- El periodo se deriva de la periodicidad del plan, no del cliente.
 IF p_fin <> (p_inicio + CASE v_plan.periodicidad
     WHEN 'mensual' THEN interval '1 month'
     WHEN 'anual' THEN interval '1 year' END) THEN RETURN false; END IF;
 SELECT * INTO v_pago FROM public.pagos_tappad
  WHERE id=p_pago AND suscripcion_id=p_suscripcion FOR UPDATE;
 IF NOT FOUND OR v_pago.estado <> 'pagado'
    OR v_pago.proveedor_cobro IS DISTINCT FROM 'mercadopago_produccion'
    OR nullif(btrim(v_pago.referencia_externa),'') IS NULL
    OR v_pago.monto_mxn <> v_plan.precio_mxn
    OR v_pago.fecha_pago IS NULL OR v_pago.fecha_pago > transaction_timestamp()

    OR p_evidencia->>'payment_id' IS DISTINCT FROM v_pago.referencia_externa
    OR p_evidencia->>'preapproval_id' IS DISTINCT FROM v_sub.referencia_externa THEN
   RETURN false;
 END IF;
 -- La clave UNIQUE(pago_id) protege contra aplicaciones duplicadas.
 -- No se sobreescribe una activacion existente: requiere conciliacion manual.
 IF EXISTS (SELECT 1 FROM public.activaciones_comerciales_tappad
            WHERE pago_id=p_pago) THEN RETURN false; END IF;
 INSERT INTO public.activaciones_comerciales_tappad
 (cliente_id,suscripcion_id,pago_id,periodo_inicio,periodo_fin,estado,evidencia_proveedor)
 VALUES (p_cliente,p_suscripcion,p_pago,p_inicio,p_fin,'aplicada',p_evidencia)
 RETURNING id INTO v_activacion;
 UPDATE public.suscripciones_tappad
 SET estado='activa',fin_periodo=p_fin,actualizado_en=transaction_timestamp()
 WHERE id=p_suscripcion;
 INSERT INTO public.acceso_comercial_tappad
 (cliente_id,suscripcion_id,estado,origen,habilitado_desde,vigente_hasta,ultima_verificacion,actualizado_en)
 VALUES (p_cliente,p_suscripcion,'habilitado','mercadopago_produccion',
         p_inicio,p_fin,transaction_timestamp(),transaction_timestamp())
 ON CONFLICT (cliente_id) DO UPDATE
 SET suscripcion_id=EXCLUDED.suscripcion_id,estado=EXCLUDED.estado,
 origen=EXCLUDED.origen,habilitado_desde=EXCLUDED.habilitado_desde,
 vigente_hasta=EXCLUDED.vigente_hasta,ultima_verificacion=EXCLUDED.ultima_verificacion,
 actualizado_en=EXCLUDED.actualizado_en;
 RETURN v_activacion IS NOT NULL;
END;
$$;
-- NO conceder EXECUTE a service_role hasta que exista una capa
-- verificadora aislada: service_role por si solo no prueba origen confiable.
REVOKE ALL ON FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(
 bigint,bigint,bigint,timestamptz,timestamptz,jsonb
) FROM PUBLIC, anon, authenticated, service_role;
-- REVISAR ANTES DE APLICAR:
-- 1. Un backend comprometido podria falsificar p_evidencia.
-- 2. Constraint PRIMARY KEY(cliente_id) confirmado en la base real.
-- 3. Regla de renovacion conservadora: exige continuidad exacta.
--    Cobros anticipados son admisibles; ventanas de gracia requieren diseno.
-- 4. El origen confiable de la evidencia NO esta implementado: BLOQUEANTE.
-- 5. No aplicar este borrador a produccion sin revisar los puntos anteriores.

-- Permisos mínimos del ejecutor privado. Aplicar únicamente tras validación.
GRANT USAGE ON SCHEMA public,tappad_internal TO tappad_activador_privado;
GRANT SELECT ON public.activaciones_comerciales_tappad TO tappad_activador_privado;
GRANT UPDATE (id) ON public.pagos_tappad TO tappad_activador_privado;
GRANT UPDATE (estado,fin_periodo,actualizado_en) ON public.suscripciones_tappad TO tappad_activador_privado;
GRANT INSERT (cliente_id,suscripcion_id,pago_id,periodo_inicio,periodo_fin,estado,evidencia_proveedor) ON public.activaciones_comerciales_tappad TO tappad_activador_privado;
GRANT INSERT, UPDATE ON public.acceso_comercial_tappad TO tappad_activador_privado;
CREATE POLICY tappad_activador_lock_pagos ON public.pagos_tappad FOR UPDATE TO tappad_activador_privado USING (true) WITH CHECK (false);
CREATE POLICY tappad_activador_select_activaciones ON public.activaciones_comerciales_tappad FOR SELECT TO tappad_activador_privado USING (true);
CREATE POLICY tappad_activador_insert_activaciones ON public.activaciones_comerciales_tappad FOR INSERT TO tappad_activador_privado WITH CHECK (estado='aplicada');
CREATE POLICY tappad_activador_update_suscripciones ON public.suscripciones_tappad FOR UPDATE TO tappad_activador_privado USING (true) WITH CHECK (estado='activa');
CREATE POLICY tappad_activador_insert_acceso ON public.acceso_comercial_tappad FOR INSERT TO tappad_activador_privado WITH CHECK (estado='habilitado' AND origen='mercadopago_produccion');
CREATE POLICY tappad_activador_update_acceso ON public.acceso_comercial_tappad FOR UPDATE TO tappad_activador_privado USING (true) WITH CHECK (estado='habilitado' AND origen='mercadopago_produccion');
DO $$
DECLARE seq text;
BEGIN
 seq := pg_get_serial_sequence('public.activaciones_comerciales_tappad','id');
 IF seq IS NOT NULL THEN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO tappad_activador_privado',seq); END IF;
END $$;
GRANT EXECUTE ON FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb) TO tappad_activador_privado;
