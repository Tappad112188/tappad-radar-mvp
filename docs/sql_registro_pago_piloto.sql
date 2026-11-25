BEGIN;
GRANT INSERT (suscripcion_id,monto_mxn,estado,proveedor_cobro,referencia_externa,fecha_pago) ON public.pagos_tappad TO tappad_activador_privado;
DO $$ BEGIN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO tappad_activador_privado',pg_get_serial_sequence('public.pagos_tappad','id')); END $$;
DROP POLICY IF EXISTS tappad_insert_pago_piloto ON public.pagos_tappad;
CREATE POLICY tappad_insert_pago_piloto ON public.pagos_tappad FOR INSERT TO tappad_activador_privado WITH CHECK (suscripcion_id=5 AND monto_mxn=449 AND estado='pagado' AND proveedor_cobro='mercadopago_produccion' AND referencia_externa ~ '^[0-9]+$' AND fecha_pago<=now());
CREATE OR REPLACE FUNCTION tappad_internal.registrar_pago_piloto(pid text,fecha timestamptz) RETURNS bigint LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE r public.pagos_tappad%ROWTYPE;
BEGIN
 IF session_user<>'tappad_login_activacion' OR current_user<>'tappad_activador_privado' OR pid IS NULL OR pid !~ '^[0-9]{1,32}$' OR fecha IS NULL OR fecha>now() THEN RAISE EXCEPTION 'registro_no_autorizado'; END IF;
 PERFORM 1 FROM public.suscripciones_tappad WHERE id=5 AND cliente_id=4 AND plan_id=1 AND proveedor_cobro='mercadopago_produccion' AND referencia_externa='dbc554730f1141a48cf73881a4e9eb96' AND estado IN ('pendiente','activa') FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'piloto_invalido'; END IF;
 INSERT INTO public.pagos_tappad(suscripcion_id,monto_mxn,estado,proveedor_cobro,referencia_externa,fecha_pago) VALUES(5,449,'pagado','mercadopago_produccion',pid,fecha) ON CONFLICT(proveedor_cobro,referencia_externa) DO NOTHING;
 SELECT * INTO STRICT r FROM public.pagos_tappad WHERE proveedor_cobro='mercadopago_produccion' AND referencia_externa=pid;
 IF r.suscripcion_id<>5 OR r.monto_mxn<>449 OR r.estado<>'pagado' OR r.fecha_pago IS DISTINCT FROM fecha THEN RAISE EXCEPTION 'pago_inconsistente'; END IF;
 RETURN r.id;
END $$;
REVOKE ALL ON FUNCTION tappad_internal.registrar_pago_piloto(text,timestamptz) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION tappad_internal.registrar_pago_piloto(text,timestamptz) TO tappad_activador_privado;
COMMIT;