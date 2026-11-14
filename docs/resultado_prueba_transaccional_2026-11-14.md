# Prueba transaccional de activacion (14-11-2026)

Se ejecutó directamente en Supabase una transacción con datos sintéticos aislados,
seguida de ROLLBACK. No hubo consultas a Mercado Pago ni pagos reales.

## Casos ejecutados

- Cliente, plan mensual de MXN 449, suscripcion y pago de QA insertados
  temporalmente con ID -990014.
- Invocación 1 de tappad_internal.tappad_aplicar_activacion_comercial:
  devuelve true (de lo contrario el bloque DO lanza excepción).
- Invocación 2 con mismo pago: devuelve false (de lo contrario lanza excepción).
- Antes del ROLLBACK, el bloque DO verificó una activación aplicada,
  suscripción activa y acceso habilitado; cualquier incumplimiento aborta.
- ROLLBACK ejecutado sin errores.
- Consulta independiente posterior confirmó 0 clientes QA, 0 activaciones QA,
  0 accesos QA, 0 activaciones comerciales reales y 0 accesos habilitados.

## Límite de seguridad

La evidencia de pago fue SINTETICA, NO verificada criptográficamente.
El test prueba atomicidad funcional y duplicados, NO la identidad del pagador,
la autorización de un worker ni la verificación de pagos por Mercado Pago.
NO desplegar worker productivo ni habilitar planes/cobros basándose solo en esto.
El rol tappad_activador_privado es NOLOGIN; no existe una credencial de
worker productivo aprovisionada. Requiere identidad privada, permisos RLS,
gestión de secretos, validación de vendedor y prueba con sandbox de proveedor.
