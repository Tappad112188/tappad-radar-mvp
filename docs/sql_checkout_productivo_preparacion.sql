BEGIN;
CREATE OR REPLACE FUNCTION public.tappad_reservar_checkout_productivo(p_cliente bigint,p_plan bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE s public.suscripciones_tappad%ROWTYPE;
a public.mercadopago_intentos_contratacion_tappad%ROWTYPE;
BEGIN
 PERFORM pg_catalog.pg_advisory_xact_lock(784221, p_cliente::integer);
 PERFORM 1 FROM public.clientes WHERE id=p_cliente AND activo IS TRUE;
 IF NOT FOUND THEN RAISE EXCEPTION 'cliente_no_habilitado'; END IF;
 PERFORM 1 FROM public.planes_tappad p JOIN public.mercadopago_planes_tappad m ON m.plan_id=p.id AND m.entorno='produccion' WHERE p.id=p_plan AND (p.activo IS TRUE OR (p_cliente=4 AND p_plan=1)) AND ((p.periodicidad='mensual' AND p.precio_mxn=449) OR (p.periodicidad='anual' AND p.precio_mxn=4490));
 IF NOT FOUND THEN RAISE EXCEPTION 'plan_no_habilitado'; END IF;
 IF EXISTS (SELECT 1 FROM public.suscripciones_tappad WHERE cliente_id=p_cliente AND proveedor_cobro='mercadopago_produccion' AND estado IN ('activa','suspendida','prueba')) THEN RAISE EXCEPTION 'suscripcion_existente'; END IF;
 SELECT * INTO s FROM public.suscripciones_tappad WHERE cliente_id=p_cliente AND proveedor_cobro='mercadopago_produccion' AND estado='pendiente' ORDER BY id LIMIT 1 FOR UPDATE;
 IF FOUND THEN
 IF s.plan_id IS DISTINCT FROM p_plan THEN RAISE EXCEPTION 'otro_plan_pendiente'; END IF;
 ELSE
 INSERT INTO public.suscripciones_tappad(cliente_id,plan_id,estado,proveedor_cobro) VALUES(p_cliente,p_plan,'pendiente','mercadopago_produccion') RETURNING * INTO s;
 END IF;
 INSERT INTO public.mercadopago_intentos_contratacion_tappad(suscripcion_id,entorno,estado) VALUES(s.id,'produccion','preparado') ON CONFLICT(suscripcion_id,entorno) DO NOTHING;
 SELECT * INTO STRICT a FROM public.mercadopago_intentos_contratacion_tappad WHERE suscripcion_id=s.id AND entorno='produccion';
 RETURN jsonb_build_object('suscripcion_id',s.id,'intento_id',a.id,'estado',a.estado,'referencia',a.idempotency_key,'preapproval_id',a.mercadopago_preapproval_id);
END;
$$;
REVOKE ALL ON FUNCTION public.tappad_reservar_checkout_productivo(bigint,bigint) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.tappad_reservar_checkout_productivo(bigint,bigint) TO service_role;
COMMIT;
