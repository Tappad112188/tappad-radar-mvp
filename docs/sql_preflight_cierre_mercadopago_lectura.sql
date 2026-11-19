-- TAPPAD Radar / Mercado Pago: preflight seguro y de SOLO LECTURA.
-- No modifica datos, roles, permisos, ni funciones.
-- Ejecutar antes de cualquier migracion comercial.
SELECT current_database() AS base, current_setting('server_version') AS postgres_version;
SELECT version, name FROM supabase_migrations.schema_migrations
WHERE name ILIKE '%comercial%' OR name ILIKE '%reversion%'
ORDER BY version DESC;
SELECT c.conname, pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
WHERE c.conrelid='public.pagos_tappad'::regclass
  AND c.conname='pagos_tappad_estado_check';
SELECT n.nspname AS esquema,p.proname AS funcion,p.prosecdef AS security_definer,
       p.proacl AS permisos
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='tappad_internal'
  AND p.proname IN ('conciliar_reversion_pago','tappad_aplicar_activacion_comercial');
SELECT rolname,rolcanlogin,rolbypassrls
FROM pg_roles WHERE rolname IN ('tappad_activador_privado','tappad_reversion_privada')
ORDER BY rolname;
SELECT schemaname,tablename,rowsecurity
FROM pg_tables WHERE schemaname='public'
AND tablename IN ('pagos_tappad','suscripciones_tappad','acceso_comercial_tappad','activaciones_comerciales_tappad');
-- IMPORTANTE: la existencia de un workflow en GitHub no prueba que exista
-- un ejecutor privado autorizado para escribir. Nunca activar por defecto.
