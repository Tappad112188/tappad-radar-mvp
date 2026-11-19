# Revisión final de seguridad — Mercado Pago
Fecha: 2026-11-19. Rama: desarrollo-registro-proveedores.

## Resultado
**Preparación avanzada, NO AUTORIZADO para aplicar a producción.**
La CI 44639337916 pasó el fixture ampliado y las 13 integraciones, pero la réplica no contiene todas las relaciones y triggers productivos. No se realizó DDL ni escrituras productivas.

## Hallazgos y acciones
1. Corregida firma errónea de la función privada de activación en `docs/sql_gate_despliegue_mercadopago_lectura.sql`. La función borrador recibe seis parámetros y es `SECURITY INVOKER`, no `DEFINER`.
2. La compuerta ahora bloquea si `anon` o `authenticated` tienen EXECUTE en la función privada de reversión.
3. El borrador de reversión declara `SECURITY INVOKER`, fija `search_path=pg_catalog`, revoca permisos de PUBLIC y valida coincidencia de referencias remotas. La validación de vendedor y pago contra Mercado Pago **depende del worker**: no se debe exponer la función como endpoint público.
4. El rol privado tiene `NOLOGIN` y `NOBYPASSRLS`, pero recibe permisos directos de UPDATE sobre estado de pagos y suscripciones para bloquear filas. Revisar y justificar el permiso de UPDATE de suscripciones (solo bloqueo) y evitar conceder membresía a roles web.
5. El script `sql_preparacion_reversion_privada_NO_APLICAR.sql` no es idempotente por `CREATE POLICY` y el preflight de estado; aplicar una sola vez, con revisión de diff y rollback.
6. La CI ejecuta un esquema aproximado. Aún faltan claves foráneas a clientes/planes y revisión de triggers, propietarios, grants efectivos y secuencias reales.
7. La tabla de auditoría contiene evidencia JSON: aplicar minimización de datos, retención y acceso privado.
8. La función usa una restricción UNIQUE(pago_id, estado_nuevo), evitando duplicados del mismo estado. Probar reversión de periodos históricos y cobros múltiples antes de automatizar.
9. Confirmar respaldo recuperable, política de migraciones, disponibilidad del servicio y ausencia de secretos en el repositorio.

## Checklist obligatorio antes de aplicar
- [ ] CI verde sobre commit final y revisión humana del SQL exacto.
- [ ] Fixture de CI fiel a FKs, CHECK, triggers y grants reales.
- [ ] Pruebas de concurrencia de activación/reversión bajo roles privados y ciclos sucesivos.
- [ ] Verificación de permisos PUBLIC/anon/authenticated y membresías.
- [ ] Validación de worker y consulta remota al proveedor; credenciales en secretos.
- [ ] Respaldo y procedimiento de reversión probado.
- [ ] Aprobación explícita de ejecución productiva.
- [ ] Aplicar migración versionada y ejecutar gate de solo lectura.
- [ ] Prueba supervisada sin cargos ni cambios a clientes reales.

## Observación de seguridad Supabase
El asesor informa 13 tablas con RLS sin políticas (puede ser denegación intencional) y protección de contraseñas filtradas deshabilitada. Revisar de manera independiente: https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection
