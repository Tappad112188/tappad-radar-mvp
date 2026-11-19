# Cierre técnico de código y límites del despliegue — Mercado Pago

Fecha: 2026-11-19. Rama: desarrollo-registro-proveedores.

## Aprobado en CI aislada
- PostgreSQL 17 temporal, suite de integración, migración/RLS, casos de concurrencia y pruebas de identidad: ejecución **44641133948**, exitosa, commit **b7e2a629**.
- Pruebas HTML: ejecución **44641133828**, exitosa.
- Ejecutor de reversión: usa `SET LOCAL ROLE tappad_reversion_privada` y rechaza identidades administrativas o con BYPASSRLS.
- Prueba del worker con usuario de LOGIN separado, NOINHERIT, y rol privado NOLOGIN con membresía SET; solo en CI.
- Workflows manuales de activación y reversión preparados; reversión requiere interruptor de habilitación explícito.

## No completado en producción
- No se han aplicado migraciones de reversión ni de activación; la última compuerta productiva de solo lectura devolvió `BLOQUEADO_PENDIENTE_MIGRACION`.
- No se ha creado ni verificado una copia restaurable de la base productiva.
- No se ha creado ni auditado el LOGIN dedicado en Supabase real; no hay evidencia de DSN TLS y permisos efectivos del ejecutor.
- No se han verificado en GitHub los revisores obligatorios de los entornos ni la disponibilidad de secretos del entorno.
- La reconciliación periódica desatendida todavía no está configurada ni validada.
- No se han realizado cobros reales, activaciones ni suspensiones de acceso durante este trabajo.

## Criterio para liberar producción
No declarar el módulo desplegado hasta: (1) respaldo y restauración probados, (2) usuario técnico restringido y credenciales TLS verificadas, (3) migración productiva aprobada y aplicada, (4) compuerta de solo lectura aprobada después del DDL, (5) prueba integral supervisada y aprobación separada para escrituras/cobros, (6) automatización recurrente y monitoreo aprobados.

**La CI verde demuestra funcionamiento aislado, no recuperabilidad ni seguridad efectiva de producción.**
