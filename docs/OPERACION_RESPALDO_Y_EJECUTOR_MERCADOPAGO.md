# Operación segura, respaldo y ejecutor — Mercado Pago

Estado: PREPARADO, SIN AUTORIZACIÓN DE CAMBIOS PRODUCTIVOS.

## Ejecutor elegido
GitHub Actions manual, sin servicio adicional de pago:
- Activación: `.github/workflows/activacion-comercial-privada.yml` (entorno `activacion-comercial`).
- Reversión: `.github/workflows/reversion-comercial-privada.yml` (entorno `reversion-comercial`).
- Ambos requieren confirmación de texto y secretos. El ejecutor de reversión exige además `TAPPAD_HABILITAR_REVERSION_PRODUCCION=SI`; **no configurar ese valor antes de la autorización de producción**.
- La concurrencia de reversión se serializa por pago interno; el bloqueo transaccional en PostgreSQL sigue siendo la defensa primaria.
- **No hay automatización recurrente de reversión** ni webhook público. Una ejecución manual no sustituye un worker periódico para un SaaS plenamente automático.
- Configurar en GitHub Settings > Environments ambos entornos con revisores requeridos cuando el plan del repositorio lo permita. Comprobar configuración real antes de ejecutar.
- Secretos mínimos de reversión: `TAPPAD_POSTGRES_DSN`, `TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN`, `TAPPAD_MERCADOPAGO_SELLER_ID`, y el interruptor de habilitación. El DSN debe estar restringido a conexión TLS y a un rol autorizado; nunca guardar contraseñas en archivos, logs ni commits.
- Revisar que la cuenta PostgreSQL usada pueda `SET ROLE tappad_reversion_privada` o usar un modelo de privilegios que ejecute con el rol adecuado. **El worker actual NO hace SET ROLE**, por lo que la identidad efectiva de ejecución debe auditarse antes de producción. No otorgar permisos excesivos como solución.

## Respaldo previo (sin inventar copia existente)
1. En Supabase Dashboard > Database > Backups verificar si existe respaldo recuperable y cuál es su cobertura según el plan. Una copia programada no equivale a restauración probada.
2. Si no hay respaldo disponible, obtener exportación cifrada y recuperable de esquema/datos críticos con herramienta compatible y conexión TLS, almacenarla fuera del repositorio; comprobar integridad y restauración en PostgreSQL aislado.
3. Registrar fecha/hora, versión PostgreSQL, hash del respaldo, alcance y custodio sin publicar datos sensibles.
4. Probar restauración en instancia temporal y comprobar conteos y restricciones; si no se puede probar, **NO aplicar DDL productivo**.
5. No prometer restauración instantánea ni asumir disponibilidad de PITR en el plan gratuito.

## Despliegue condicionado
1. Confirmar CI final verde, diff exacto, seguridad de permisos y mecanismo de identidad del worker.
2. Obtener autorización explícita para aplicar migración productiva, separada de cualquier autorización para cobrar o activar accesos.
3. Aplicar DDL versionado y ejecutar `docs/sql_gate_despliegue_mercadopago_lectura.sql` (solo lectura).
4. Si falla una condición, dejar workers deshabilitados y usar procedimiento de recuperación documentado. **No revertir estados de pagos ni borrar auditoría automáticamente**.
5. Ejecutar una prueba supervisada sin cobro real y verificar auditoría, permisos y RLS.

## Pendientes
- [ ] Configuración y revisión efectiva de entornos GitHub y secretos (sin exponer valores).
- [ ] Identidad PostgreSQL y permisos del ejecutor probados bajo rol real.
- [ ] Respaldo creado y restauración verificada.
- [ ] Migración versionada y autorización de producción.
- [ ] Definir reconciliación periódica automática antes del lanzamiento comercial.

## Hallazgo bloqueante: identidad NOLOGIN frente al ejecutor actual

La función SQL es `SECURITY INVOKER` y el rol `tappad_reversion_privada` se crea con `NOLOGIN`. El worker Python actual abre la conexión mediante el DSN y **no ejecuta `SET ROLE`**. Por tanto, no hay evidencia de que opere realmente bajo el rol restringido. No se debe compensar concediendo UPDATE/INSERT a `service_role` o usando credenciales administrativas permanentes.

Se agregó `verificar_identidad_ejecutor_postgres.py` y el workflow manual `verificar-identidad-postgres-mercadopago.yml`. Este control es solo lectura y **fallará cerrado** si la identidad no es exactamente `tappad_reversion_privada` sin BYPASSRLS. Dado que el rol es NOLOGIN, ese resultado requiere diseñar y validar una transición explícita de rol (o mecanismo equivalente) antes de usar el worker. El control aún no está ejecutado contra un DSN real.

**Respaldo:** no se ha creado ni restaurado una copia de producción; la documentación del procedimiento no equivale a un respaldo probado. **No desplegar** hasta cerrar ambos puntos.
