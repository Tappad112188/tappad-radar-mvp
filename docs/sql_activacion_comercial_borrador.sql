-- BORRADOR NO APLICADO. Solo ejecutar tras validar proveedor en servidor.
-- Nunca aceptar evidencia JSON del navegador como verificacion de pago.
-- El llamador de confianza debe consultar API de Mercado Pago, verificar
-- identidad del vendedor, preapproval, payment, importe, moneda y periodo.
-- Este procedimiento aplica atomicamente una evidencia previamente validada.
CREATE OR REPLACE FUNCTION public.tappad_aplicar_activacion_comercial(
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
BEGIN
 IF p_cliente IS NULL OR p_suscripcion IS NULL OR p_pago IS NULL
    OR p_inicio IS NULL OR p_fin IS NULL OR p_evidencia IS NULL
    OR p_inicio > transaction_timestamp()
    OR p_fin <= transaction_timestamp() OR p_fin <= p_inicio
    OR p_evidencia->>'verificacion_remota' <> 'confirmada'
    OR p_evidencia->>'entorno' <> 'produccion' THEN
   RETURN false;
 END IF;
 SELECT * INTO v_sub FROM public.suscripciones_tappad
  WHERE id=p_suscripcion AND cliente_id=p_cliente
  FOR UPDATE;
 IF NOT FOUND OR v_sub.proveedor_cobro <> 'mercadopago_produccion'
    OR v_sub.estado NOT IN ('pendiente','activa') OR
    nullif(btrim(v_sub.referencia_externa),'') IS NULL THEN RETURN false; END IF;
 SELECT * INTO v_plan FROM public.planes_tappad WHERE id=v_sub.plan_id;
 IF NOT FOUND OR NOT v_plan.activo THEN RETURN false; END IF;
 SELECT * INTO v_pago FROM public.pagos_tappad
  WHERE id=p_pago AND suscripcion_id=p_suscripcion FOR UPDATE;
 IF NOT FOUND OR v_pago.estado <> 'pagado'
    OR v_pago.proveedor_cobro <> 'mercadopago_produccion'
    OR nullif(btrim(v_pago.referencia_externa),'') IS NULL
    OR v_pago.monto_mxn <> v_plan.precio_mxn
    OR v_pago.fecha_pago IS NULL OR v_pago.fecha_pago > transaction_timestamp()
    OR p_evidencia->>'payment_id' <> v_pago.referencia_externa
    OR p_evidencia->>'preapproval_id' <> v_sub.referencia_externa THEN
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
REVOKE ALL ON FUNCTION public.tappad_aplicar_activacion_comercial(
 bigint,bigint,bigint,timestamptz,timestamptz,jsonb
) FROM PUBLIC, anon, authenticated, service_role;
-- REVISAR ANTES DE APLICAR:
-- 1. Un backend comprometido podria falsificar p_evidencia.
-- 2. No se ha probado constraint ON CONFLICT(cliente_id) en esta instalacion.
-- 3. No se ha resuelto correctamente el periodo de renovacion.
-- 4. No aplicar este borrador a produccion sin revisar los puntos anteriores.
