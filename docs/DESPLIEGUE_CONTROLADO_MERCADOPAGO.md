# Despliegue controlado Mercado Pago — TAPPAD Radar
Estado: **BLOQUEADO PARA PRODUCCION** hasta completar verificaciones. Sin costos adicionales.

## Evidencia verificada
- GitHub Actions 44638882426: 4 compuertas + 1 migracion/RLS + 13 integraciones, todas aprobadas.
- Auditoria Supabase (solo lectura, 2026-11-19): cuatro tablas comerciales tienen RLS.
- En produccion faltan: constraint `contracargo`, funcion `tappad_internal.conciliar_reversion_pago`, rol `tappad_reversion_privada`.
- Se comprobo que la estructura real tiene columnas y constraints adicionales (monto_mxn, plan_id, origen, fechas y FKs), que no estan replicadas plenamente en CI.
- Nueva prueba de llamada bajo rol privado: `tests/test_migracion_reversion_postgres_aislada.py` (commit bc1d8085); **aun sin resultado confirmado**.

## Orden de despliegue (sin ejecucion automatica)
1. Confirmar respaldo recuperable y ventana de mantenimiento; revisar permisos de acceso al proyecto.
2. Ejecutar `docs/sql_preflight_cierre_mercadopago_lectura.sql` y `docs/sql_gate_despliegue_mercadopago_lectura.sql` en solo lectura; registrar resultado.
3. En PostgreSQL efimero, probar ambas migraciones con datos ficticios, invocacion con SET ROLE y RLS, concurrencia y reversion.
4. Revisar DDL final: `docs/sql_conciliacion_reversion_mercadopago_borrador.sql` antes de `docs/sql_preparacion_reversion_privada_NO_APLICAR.sql`; eliminar permisos innecesarios y validar idempotencia de politicas/roles.
5. Revisar privilegios reales de `anon`, `authenticated`, `service_role`, propietario de funcion y rol de ejecucion. NO otorgar LOGIN al rol `tappad_reversion_privada` ni exponer `tappad_internal` en Data API.
6. Crear migracion versionada con Supabase CLI y revisar diff. Aplicar en una transaccion controlada **solo tras autorizar cambio productivo**; no activar worker ni cambiar estado de pagos/clientes.
7. Volver a ejecutar gate y asesores de seguridad. Verificar que los nuevos objetos son privados y que no cambiaron datos comerciales.
8. Probar reconciliacion del pago existente en solo lectura, luego prueba integral supervisada con datos de prueba. Habilitar escrituras y alertas comerciales solamente tras aprobacion independiente.

## Criterios de rechazo
- Fallos en cualquier test de PostgreSQL o diferencias con esquema real.
- Falta de respaldo, DSN privado, aislamiento de secretos, control de ejecucion o pruebas de concurrencia.
- Funcion `SECURITY DEFINER` accesible por roles publicos, permisos `PUBLIC EXECUTE`, RLS ausente o credenciales en repositorio.
- Evidencia Mercado Pago no verificada directamente por backend.
- Activacion o suspension de un periodo no respaldado por el pago correcto.

## Seguridad adicional
Supabase Security Advisor notifico 13 tablas con RLS sin politicas (podrian ser denegacion intencional) y proteccion contra contrasenas filtradas deshabilitada. Revisar sin conceder politicas generales.

**No activar** `TAPPAD_HABILITAR_ACTIVACION_PRODUCCION` ni `TAPPAD_HABILITAR_REVERSION_PRODUCCION` en esta fase.
