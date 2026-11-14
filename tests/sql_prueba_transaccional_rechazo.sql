-- Prueba transaccional no destructiva sobre la suscripcion de prueba.
-- Se ejecuta en una unica sesion SQL y revierte todo.
BEGIN;
SELECT tappad_internal.tappad_aplicar_activacion_comercial(
  4,1,1,now(),now()+interval '1 month',
  '{"verificacion_remota":"confirmada","entorno":"produccion","seller_id":"fake","payment_id":"fake","preapproval_id":"fake"}'::jsonb
) AS debe_ser_false;
ROLLBACK;

-- Prueba de permisos: debe retornar false en los tres roles expuestos.
SELECT has_function_privilege('anon',
 'tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb)',
 'EXECUTE') AS anon,
 has_function_privilege('authenticated',
 'tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb)',
 'EXECUTE') AS authenticated,
 has_function_privilege('service_role',
 'tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb)',
 'EXECUTE') AS service_role;
