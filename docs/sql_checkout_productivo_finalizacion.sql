BEGIN;
CREATE OR REPLACE FUNCTION public.tappad_finalizar_checkout_productivo(p_intento bigint,p_preapproval text)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE sid bigint; a public.mercadopago_intentos_contratacion_tappad%ROWTYPE; s public.suscripciones_tappad%ROWTYPE;
BEGIN
 IF p_preapproval IS NULL OR p_preapproval !~ '^[a-zA-Z0-9_-]{1,128}$' THEN RAISE EXCEPTION 'referencia_invalida'; END IF;
 SELECT suscripcion_id INTO STRICT sid FROM public.mercadopago_intentos_contratacion_tappad WHERE id=p_intento AND entorno='produccion';
 SELECT * INTO STRICT s FROM public.suscripciones_tappad WHERE id=sid FOR UPDATE;
 SELECT * INTO STRICT a FROM public.mercadopago_intentos_contratacion_tappad WHERE id=p_intento AND entorno='produccion' FOR UPDATE;
 IF s.proveedor_cobro IS DISTINCT FROM 'mercadopago_produccion' OR s.estado IS DISTINCT FROM 'pendiente' THEN RAISE EXCEPTION 'suscripcion_invalida'; END IF;
 IF a.estado='creado' AND a.mercadopago_preapproval_id=p_preapproval AND s.referencia_externa=p_preapproval THEN RETURN; END IF;
 IF a.estado IS DISTINCT FROM 'en_proceso' OR a.mercadopago_preapproval_id IS NOT NULL OR s.referencia_externa IS NOT NULL THEN RAISE EXCEPTION 'intento_invalido'; END IF;
 UPDATE public.suscripciones_tappad SET referencia_externa=p_preapproval,actualizado_en=now() WHERE id=sid;
 UPDATE public.mercadopago_intentos_contratacion_tappad SET estado='creado',mercadopago_preapproval_id=p_preapproval,actualizado_en=now() WHERE id=p_intento;
END; $$;
REVOKE ALL ON FUNCTION public.tappad_finalizar_checkout_productivo(bigint,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.tappad_finalizar_checkout_productivo(bigint,text) TO service_role;
COMMIT;