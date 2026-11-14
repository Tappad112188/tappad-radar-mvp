-- BORRADOR NO APLICADO. Revisar con pruebas transaccionales antes de desplegar.
-- Reemplaza el punto de entrada RPC existente; mantiene la firma y permisos.
-- Solo service_role puede ejecutarlo (verificar privilegios efectivos antes de aplicar).
-- El bloqueo FOR SHARE serializa cambios a filas comerciales con la reserva.
CREATE OR REPLACE FUNCTION public.tappad_reservar_lote(
    p_cliente bigint, p_licitaciones bigint[]
) RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_suscripcion bigint;
    v_fin timestamptz;
    v_periodo timestamptz;
    v_proveedor text;
    v_pago bigint;
BEGIN
    IF p_cliente IS NULL OR p_licitaciones IS NULL
       OR cardinality(p_licitaciones) = 0 THEN
        RETURN false;
    END IF;

    SELECT a.suscripcion_id, a.vigente_hasta,
           s.fin_periodo, s.proveedor_cobro
      INTO v_suscripcion, v_fin, v_periodo, v_proveedor
      FROM public.acceso_comercial_tappad a
      JOIN public.suscripciones_tappad s
        ON s.id = a.suscripcion_id AND s.cliente_id = a.cliente_id
     WHERE a.cliente_id = p_cliente
       AND a.estado = 'habilitado'
       AND s.estado = 'activa'
       AND s.proveedor_cobro = 'mercadopago_produccion'
       AND a.vigente_hasta > transaction_timestamp()
       AND s.fin_periodo >= a.vigente_hasta
     FOR SHARE OF a, s;

    IF v_suscripcion IS NULL OR v_fin IS NULL
       OR v_periodo <= transaction_timestamp() THEN
        RETURN false;
    END IF;

    SELECT ac.pago_id
      INTO v_pago
      FROM public.activaciones_comerciales_tappad ac
      JOIN public.pagos_tappad p
        ON p.id = ac.pago_id AND p.suscripcion_id = ac.suscripcion_id
     WHERE ac.cliente_id = p_cliente
       AND ac.suscripcion_id = v_suscripcion
       AND ac.estado = 'aplicada'
       AND ac.periodo_inicio <= transaction_timestamp()
       AND ac.periodo_fin >= v_fin
       AND ac.periodo_fin > transaction_timestamp()
       AND p.estado = 'pagado'
       AND p.proveedor_cobro = v_proveedor
       AND nullif(btrim(p.referencia_externa), '') IS NOT NULL
     ORDER BY ac.periodo_fin DESC
     LIMIT 1
     FOR SHARE OF ac, p;

    IF v_pago IS NULL THEN
        RETURN false;
    END IF;

    RETURN tappad_internal.reservar_lote(p_cliente, p_licitaciones);
END;
$$;

REVOKE ALL ON FUNCTION public.tappad_reservar_lote(bigint,bigint[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.tappad_reservar_lote(bigint,bigint[]) TO service_role;

-- IMPORTANTE: Esta compuerta NO verifica la API de Mercado Pago en vivo.
-- Solo debe aplicarse tras implementar un conciliador autenticado que
-- escriba activaciones aplicadas y pagos verificados.
-- Auditar otros INSERT directos sobre notificaciones_enviadas y los grants
-- de tappad_internal.reservar_lote; service_role puede omitir este RPC.
