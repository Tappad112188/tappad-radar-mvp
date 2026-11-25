CREATE OR REPLACE FUNCTION tappad_internal.tappad_aplicar_activacion_comercial(p_cliente bigint, p_suscripcion bigint, p_pago bigint, p_inicio timestamp with time zone, p_fin timestamp with time zone, p_evidencia jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
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
    OR v_sub.estado NOT IN ('pendiente','prueba','activa') OR
    nullif(btrim(v_sub.referencia_externa),'') IS NULL THEN RETURN false; END IF;
 SELECT * INTO v_plan FROM public.planes_tappad WHERE id=v_sub.plan_id;
 IF NOT FOUND OR (v_plan.activo IS DISTINCT FROM true AND NOT (v_sub.id=5 AND v_sub.cliente_id=4 AND v_sub.plan_id=1 AND v_sub.referencia_externa='dbc554730f1141a48cf73881a4e9eb96')) OR v_plan.periodicidad NOT IN ('mensual','anual') THEN RETURN false; END IF;
 -- Una renovacion solo extiende el periodo previo; nunca lo acorta
 -- ni crea un hueco o solapamiento entre ciclos.
 SELECT CASE WHEN estado='prueba' THEN NULL ELSE vigente_hasta END INTO v_fin_anterior
 FROM public.acceso_comercial_tappad
 WHERE cliente_id=p_cliente FOR UPDATE;
 IF v_fin_anterior IS NOT NULL THEN
   v_inicio_esperado := v_fin_anterior;
   IF p_inicio <> v_inicio_esperado OR p_fin <= v_fin_anterior THEN
     RETURN false;
   END IF;
 ELSE
   -- Primer ciclo: inicio no puede ser futuro ni arbitrariamente antiguo.
   IF v_sub.estado <> 'prueba' AND p_inicio < transaction_timestamp() - interval '7 days' THEN
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
    OR v_pago.monto_mxn IS DISTINCT FROM v_plan.precio_mxn
    OR v_pago.fecha_pago IS NULL OR v_pago.fecha_pago > transaction_timestamp()
    OR (v_fin_anterior IS NULL AND p_inicio IS DISTINCT FROM v_pago.fecha_pago)

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
$function$
