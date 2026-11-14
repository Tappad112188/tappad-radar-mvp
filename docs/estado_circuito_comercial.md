# Cierre del circuito de activacion comercial (estado real)

## Arquitectura

1. Worker privado consulta pagos_tappad, suscripciones_tappad y planes_tappad
   mediante credenciales de servidor.
2. Consulta directamente API Mercado Pago y verifica pago, preapproval, monto,
   moneda, estado y vendedor esperado (TAPPAD_MERCADOPAGO_SELLER_ID).
3. Abre conexion PostgreSQL PRIVADA y llama
   tappad_internal.tappad_aplicar_activacion_comercial en una transaccion.
4. La funcion bloquea duplicados mediante UNIQUE(pago_id), valida relaciones,
   plan y periodo, y actualiza suscripcion, activacion y acceso atomicamente.
5. Ante error, rollback; ante exito, commit.

## Estado y bloqueos

- La funcion SQL esta desplegada en esquema no expuesto y no admite anon,
  authenticated ni service_role.
- Existe tappad_activador_privado NOLOGIN con EXECUTE, sin acceso a tablas.
  **Por tanto, no puede completar la transaccion en este estado.**
- NO hay worker desplegado con identidad y credenciales de PostgreSQL privadas.
- No hay seller_id productivo configurado, ni pagos productivos conciliados.
- La fecha de inicio/fin aun es parametro del worker; se debe derivar de
  evidencia del proveedor y de la politica de renovacion antes de produccion.
- NO habilitar el flag TAPPAD_HABILITAR_ACTIVACION_PRODUCCION hasta cerrar esto.
- La funcion actual no valida criptograficamente p_evidencia; la autenticidad
  depende exclusivamente de un worker de confianza y su aislamiento.

## Validacion previa a produccion

1. Configurar worker servidor privado y credenciales de minimo privilegio.
2. Definir modelo de permisos de la funcion (RLS y tablas) y probar en staging.
3. Implementar calculo del ciclo de facturacion desde evidencia verificada.
4. Pruebas de rollback, pago duplicado, simultaneidad, pago cancelado, seller
   distinto y renovaciones (incluidas anticipadas).
5. Revisar CI y una transaccion integral en staging; despues aprobar despliegue.
6. Requerir aprobacion explicita para habilitar cobros o activaciones reales.

No copiar credenciales de produccion a GitHub, pruebas o frontend.
