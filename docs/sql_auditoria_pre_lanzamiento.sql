-- Auditoria comercial de solo lectura. No cambia datos ni permisos.
-- Un resultado false significa que NO debe habilitarse produccion.
SELECT
 NOT EXISTS (
   SELECT 1 FROM public.activaciones_comerciales_tappad
   WHERE estado='aplicada'
 ) AS sin_activaciones_reales,
 NOT EXISTS (
   SELECT 1 FROM public.acceso_comercial_tappad
   WHERE estado='habilitado'
 ) AS sin_accesos_habilitados,
 NOT EXISTS (
   SELECT 1 FROM public.pagos_tappad
   WHERE proveedor_cobro='mercadopago_produccion' AND estado='pagado'
 ) AS sin_pagos_productivos,
 NOT EXISTS (
   SELECT 1 FROM public.planes_tappad WHERE activo
 ) AS planes_no_publicados,
 NOT EXISTS (
   SELECT 1 FROM pg_proc p
   JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname='public'
     AND p.proname='tappad_aplicar_activacion_comercial'
 ) AS activacion_sql_no_desplegada,
 NOT EXISTS (
   SELECT 1 FROM pg_proc p
   JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname='public'
     AND p.proname IN ('tappad_preparar_activacion_transaccional','tappad_reservar_lote')
     AND (has_function_privilege('anon',p.oid,'EXECUTE')
       OR has_function_privilege('authenticated',p.oid,'EXECUTE'))
 ) AS rpcs_existentes_no_publicas;
-- ATENCION: este reporte demuestra bloqueos existentes, no valida
-- la seguridad de la futura RPC ni la integridad de evidencia remota.
