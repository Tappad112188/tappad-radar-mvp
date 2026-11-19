-- TAPPAD Radar: compuerta de despliegue, SOLO LECTURA.
-- No ejecuta DDL, no lee secretos ni datos de clientes.
WITH state AS (
 SELECT
  EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid='public.pagos_tappad'::regclass
    AND conname='pagos_tappad_estado_check'
    AND pg_get_constraintdef(oid) LIKE '%contracargo%') AS estado_contracargo_instalado,
  to_regprocedure('tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)') IS NOT NULL
    AS funcion_reversion_instalada,
  EXISTS(SELECT 1 FROM pg_roles WHERE rolname='tappad_reversion_privada'
    AND NOT rolcanlogin AND NOT rolbypassrls) AS rol_reversion_no_login,
  EXISTS(SELECT 1 FROM pg_proc WHERE oid =
    to_regprocedure('tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb)')
    AND NOT prosecdef) AS activacion_privada_invoker_instalada,
  COALESCE(has_function_privilege('anon',
    to_regprocedure('tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)'),
    'EXECUTE'),false) AS anon_puede_ejecutar_reversion,
  COALESCE(has_function_privilege('authenticated',
    to_regprocedure('tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)'),
    'EXECUTE'),false) AS authenticated_puede_ejecutar_reversion,
  (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relname IN (
      'pagos_tappad','suscripciones_tappad','acceso_comercial_tappad',
      'activaciones_comerciales_tappad') AND c.relrowsecurity) AS tablas_comerciales_con_rls
)
SELECT current_database() AS base,
       estado_contracargo_instalado,funcion_reversion_instalada,
       rol_reversion_no_login,activacion_privada_invoker_instalada,
       anon_puede_ejecutar_reversion,authenticated_puede_ejecutar_reversion,
       tablas_comerciales_con_rls,
       CASE WHEN estado_contracargo_instalado
         AND funcion_reversion_instalada AND rol_reversion_no_login
         AND NOT anon_puede_ejecutar_reversion
         AND NOT authenticated_puede_ejecutar_reversion
         AND tablas_comerciales_con_rls=4
         THEN 'DDL_VERIFICABLE_NO_AUTORIZA_COBROS'
         ELSE 'BLOQUEADO_PENDIENTE_MIGRACION'
       END AS dictamen
FROM state;
