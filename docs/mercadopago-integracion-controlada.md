# TAPPAD Radar — Mercado Pago: plan de integración controlada

Estado: diseño de implementación; NO habilita cobros.

## Precios finales
- Mensual: MXN 449.00 IVA incluido. Base 387.07, IVA 61.93.
- Anual: MXN 4,490.00 IVA incluido. Base 3,870.69, IVA 619.31.
- No se agrega IVA sobre estos importes en checkout.

## Comprobaciones ya realizadas
- /users/me devuelve cuenta test_user en México.
- GET /preapproval_plan/search responde correctamente, con cero planes existentes en la consulta.
- Los planes en public.planes_tappad están inactivos.

## Requisitos antes de crear planes
1. Verificar en documentación de Mercado Pago la compatibilidad de preapproval_plan con usuarios de prueba, la necesidad de back_url y los flujos de suscripción.
2. Crear endpoint administrativo que valide sesión y rol de administrador en servidor, no solo que exista JWT. No aceptar role o client_id desde el navegador como autorización.
3. Validar token de Mercado Pago contra /users/me y rechazar si no es test_user de México.
4. Ejecutar búsqueda antes de crear; guardar plan_id por periodicidad; evitar duplicados en reintentos.
5. No exponer access token ni service_role en el navegador, respuestas o logs.
6. Configurar webhook que verifique autenticidad de la notificación y consulte el estado a Mercado Pago antes de activar la suscripción.
7. Activar alertas únicamente cuando la suscripción/pago estén confirmados.
8. Probar rechazo, cancelación, renovación, duplicados y errores antes de producción.

## Separación fiscal
- 'Solicita factura' no modifica el total del cargo.
- CFDI individual o global según corresponda; validar tratamiento fiscal con contador.

## Condición de salida
No pasar a producción ni aceptar cobros reales sin verificación integral de la contratación y conciliación.
