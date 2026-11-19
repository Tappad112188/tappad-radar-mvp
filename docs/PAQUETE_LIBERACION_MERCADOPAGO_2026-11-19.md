# TAPPAD Radar — paquete de liberación Mercado Pago (sin costo adicional)
Fecha: 2026-11-19. Rama: desarrollo-registro-proveedores.

**Estado: preparado para validación, NO desplegado a producción.**

## Evidencia automática
- GitHub Actions PostgreSQL 17: ejecución 44638057349, 13/13 pruebas aprobadas, commit 9bfdc919.
- El workflow `.github/workflows/integracion-postgres-comercial.yml` incluye además la compuerta `tests/test_gate_lanzamiento_comercial.py` desde commit be72811.
- CI usa PostgreSQL efímero y evidencia de Mercado Pago simulada; **no es copia fiel de Supabase**.

## Migraciones candidatas, en este orden (NO APLICAR aún)
1. `docs/sql_conciliacion_reversion_mercadopago_borrador.sql`: tabla privada de auditoría y función `SECURITY INVOKER`, revoca EXECUTE público.
2. `docs/sql_preparacion_reversion_privada_NO_APLICAR.sql`: preflight de constraint, añade `contracargo`, rol `NOLOGIN`, GRANT por columna, políticas RLS.
3. Revisar el diseño de acceso: las políticas `USING(true)` de rol privado permiten todas las filas si ese rol es comprometido. Antes de desplegar, limitar el ejecutor y demostrar aislamiento real. No conceder rol privado a `anon`, `authenticated` ni `service_role`.
4. Confirmar que las columnas reales, FKs, constraints, índices, triggers, grants y secuencias coinciden con las de la migración. Ejecutar preflight `docs/sql_preflight_cierre_mercadopago_lectura.sql` solo lectura.
5. Verificar que la función de activación ya existente `tappad_internal.tappad_aplicar_activacion_comercial` es `SECURITY DEFINER` y no recibe ejecución desde roles públicos. Revisar evidencia de pago y autorización del caller.
6. Preparar rollback transaccional para cualquier error de DDL y un plan de recuperación de datos (no revertir automáticamente pagos reales).

## Prueba integral final (una sola ejecución supervisada)
- Datos de prueba sin cargo: cliente/plan/suscripción/pago simulados, con vendedor y moneda esperados.
- Contratación idempotente: doble solicitud produce una sola reserva.
- Pago rechazado o vendedor distinto: acceso NO habilitado.
- Pago válido conciliado: una sola activación, acceso habilitado, periodo correcto.
- Dos activaciones simultáneas: no duplican acceso ni auditoría.
- Reembolso y contracargo: auditoría única, acceso suspendido solo si depende del pago revertido.
- Activación contra reversión concurrente: sin deadlock y sin acceso indebidamente habilitado.
- Renovación anticipada, vencimiento y cancelación: conservar periodos ya pagados y bloquear los no pagados.
- RLS: roles `anon` y `authenticated` no pueden invocar funciones privadas ni escribir pagos/accesos; probar también rol ejecutor real.
- Alertas ComprasMX y SECOP: solo clientes con acceso comercial vigente; sin alterar extracción ni envíos existentes.
- Monitoreo y salida: logs sin secretos, comprobación de estados, apagado inmediato del worker si falla alguna invariante.

## Puertas obligatorias antes de producción
- [ ] Pruebas de migraciones contra esquema fiel de Supabase (sin crear rama con costo sin autorización).
- [ ] Pruebas RLS y concurrencia usando identidad real del ejecutor, no solo roles de CI.
- [ ] Ejecutor privado con TLS y permisos mínimos verificados; secreto PostgreSQL no expuesto a clientes.
- [ ] Conciliación real de pagos existentes en modo solo lectura y política de renovación validada.
- [ ] Migraciones revisadas y aprobadas, respaldo y plan de recuperación verificados.
- [ ] Aprobación separada para habilitar escrituras productivas y cualquier cobro nuevo.

**Prohibido** activar flags `TAPPAD_HABILITAR_ACTIVACION_PRODUCCION` o `TAPPAD_HABILITAR_REVERSION_PRODUCCION` durante estas pruebas. No ejecutar los SQL de borrador en producción.
